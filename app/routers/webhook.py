from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
from app.services.payment_service import is_duplicate_event, process_payment_event
from app.config import RAZORPAY_WEBHOOK_SECRET, PAYMENT_STATUS_MAP
import hmac
import hashlib
import logging
from app.services.supabase_service import supabase
from fastapi import BackgroundTasks

router = APIRouter()
logger = logging.getLogger(__name__)

def verify_webhook_signature(request_body: str, signature: str) -> bool:
    """Verify Razorpay webhook signature"""
    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        request_body.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

def extract_payment_details(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant payment details from webhook payload"""
    try:
        payment_data = payload.get('payload', {}).get('payment', {}).get('entity', {})
        notes = payment_data.get('notes', {})
        
        # First try to get user_id from notes
        user_id = notes.get('user_id')
        
        # If no user_id in notes, try to get from email
        if not user_id:
            user_email = notes.get('enter_your_signup_email') or payment_data.get('email')
            if user_email:
                try:
                    # Use public.users table
                    user_result = supabase.table('users').select('id').eq('email', user_email).execute()
                    user_id = user_result.data[0]['id'] if user_result.data else None
                    logger.info(f"Found user_id: {user_id} for email: {user_email}")
                except Exception as e:
                    logger.error(f"Error finding user by email: {str(e)}")
                    pass
        
        return {
            'razorpay_payment_id': payment_data.get('id'),
            'razorpay_order_id': payment_data.get('order_id'),
            'amount': int(payment_data.get('amount', 0)),
            'currency': payment_data.get('currency'),
            'status': PAYMENT_STATUS_MAP.get(payment_data.get('status'), 'unknown'),
            'payment_method': payment_data.get('method'),
            'email': payment_data.get('email'),
            'contact': payment_data.get('contact'),
            'payment_details': payment_data,
            'user_id': user_id
        }
    except Exception as e:
        logger.error(f"Error extracting payment details: {str(e)}")
        raise ValueError(f"Invalid payment payload structure: {str(e)}")

@router.post("/razorpay-webhook", name="razorpay_webhook")
async def handle_razorpay_webhook(request: Request):
    try:
        raw_body = await request.body()
        body_text = raw_body.decode()
        signature = request.headers.get('x-razorpay-signature')
        
        # Missing: Event ID Check for duplicate events
        event_id = request.headers.get('x-razorpay-event-id')
        
        # Should return 200 even if event is duplicate
        if event_id and await is_duplicate_event(event_id):
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Event already processed"}
            )
        
        logger.info(f"Received webhook with signature: {signature}")
        
        if not signature:
            logger.error("Missing webhook signature")
            raise HTTPException(status_code=400, detail="Missing webhook signature")
            
        # Verify signature
        if not verify_webhook_signature(body_text, signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
            
        # Parse payload
        payload = await request.json()
        logger.info(f"Processing webhook event: {payload.get('event')}")
        
        # Extract and process payment details
        payment_details = extract_payment_details(payload)
        logger.info(f"Extracted payment details: {payment_details}")
        
        # 1. Quick verification
        if not verify_webhook_signature(body_text, signature):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Invalid signature"}
            )
            
        # 2. Quick acknowledgment
        background_tasks = BackgroundTasks()
        background_tasks.add_task(process_payment_event, payload.get('event'), payment_details)
        
        # 3. Immediate response
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Webhook received"},
            background=background_tasks
        )
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@router.get("/razorpay-webhook/health", name="webhook_health")
async def webhook_health():
    """Health check endpoint for Razorpay"""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy"}
    )