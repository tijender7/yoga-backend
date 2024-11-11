from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
from app.services.payment_service import process_payment_event
from app.config import RAZORPAY_WEBHOOK_SECRET, PAYMENT_STATUS_MAP
import hmac
import hashlib
import logging

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
        return {
            'razorpay_payment_id': payment_data.get('id'),
            'razorpay_order_id': payment_data.get('order_id'),
            'amount': payment_data.get('amount'),
            'currency': payment_data.get('currency'),
            'status': PAYMENT_STATUS_MAP.get(payment_data.get('status'), 'unknown'),
            'payment_method': payment_data.get('method'),
            'email': payment_data.get('email'),
            'contact': payment_data.get('contact'),
            'payment_details': payment_data,  # Store complete payment details
            'user_id': payment_data.get('notes', {}).get('user_id')
        }
    except Exception as e:
        logger.error(f"Error extracting payment details: {str(e)}")
        raise ValueError("Invalid payment payload structure")

@router.post("/razorpay-webhook")
async def handle_razorpay_webhook(request: Request):
    try:
        # Get raw body and signature
        raw_body = await request.body()
        body_text = raw_body.decode()
        signature = request.headers.get('x-razorpay-signature')
        
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
        
        await process_payment_event(
            event=payload.get('event'),
            payment_details=payment_details
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Webhook processed successfully"}
        )
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )