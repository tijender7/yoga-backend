from fastapi import FastAPI, HTTPException, Request
from app.services.razorpay_service import create_payment_link
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import FRONTEND_URL, IS_DEVELOPMENT, PAYMENT_STATUS_MAP, RAZORPAY_CALLBACK_URL
from datetime import datetime
from app.services.supabase_service import supabase
from fastapi.responses import JSONResponse
from typing import Dict, Any
from pydantic import BaseModel, Field
from typing import Optional
from pydantic import EmailStr
import secrets
import os
from app.routers import auth

app = FastAPI()

# CORS configuration
origins = [
    os.getenv('FRONTEND_URL'),
    "https://api.razorpay.com",
    "https://checkout.razorpay.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HANDLED_EVENTS = {
    'payment.captured': 'Payment successful',
    'payment.failed': 'Payment failed',
    'payment.pending': 'Payment pending',
    'payment.downtime': 'Payment system downtime notification'
}

class PaymentEntity(BaseModel):
    id: str
    status: str
    amount: int
    currency: str

class PaymentPayload(BaseModel):
    payment: dict = Field(..., description="Payment details")

class WebhookPayload(BaseModel):
    event: str
    payload: Dict[str, Any]  # Make it flexible to handle different payload types

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    healthConditions: Optional[str] = None
    userId: Optional[str] = None
    username: Optional[str] = None
    interest: Optional[str] = None
    source: Optional[str] = None

@app.post("/api/create-payment")
async def create_payment_endpoint(payment_data: dict):
    try:
        amount = payment_data.get('amount')
        currency = payment_data.get('currency', 'INR')
        description = payment_data.get('description', 'Yoga Class Payment')
        user_id = payment_data.get('user_id')
        
        payment_link = await create_payment_link(
            amount=amount, 
            currency=currency, 
            description=description,
            user_id=user_id
        )
        return {"payment_link": payment_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/razorpay-webhook")
async def payment_webhook(request: Request):
    try:
        payload = await request.json()
        webhook_data = WebhookPayload(**payload)
        logger.info(f"Received webhook payload: {payload}")
        
        if webhook_data.event.startswith('payment.'):
            payment_entity = webhook_data.payload.get('payment', {}).get('entity')
            if payment_entity:
                payment_id = payment_entity.get('id')
                order_id = payment_entity.get('order_id')
                
                # Convert amount based on currency
                amount = payment_entity.get('amount', 0)
                currency = payment_entity.get('currency', 'INR')
                
                # Convert from lowest denomination to actual amount
                converted_amount = amount / 100  # Since all currencies use 100 as base
                
                # Try to get user_id from payment entity
                user_id = None
                
                # Get the email from payment entity
                email = payment_entity.get('email')
                if email:
                    # Try to get user by email
                    user_result = supabase.table('users')\
                        .select('id')\
                        .eq('email', email)\
                        .execute()
                    if user_result.data:
                        user_id = user_result.data[0].get('id')
                        logger.info(f"Found user_id {user_id} for email {email}")
                
                if payment_id:
                    # Check for existing payment
                    existing_payment = supabase.table('payments')\
                        .select('*')\
                        .eq('razorpay_payment_id', payment_id)\
                        .execute()
                    
                    payment_data = {
                        'razorpay_payment_id': payment_id,
                        'status': PAYMENT_STATUS_MAP.get(payment_entity['status'], 'pending'),
                        'amount': converted_amount,  # Store converted amount
                        'currency': currency,
                        'payment_method': 'razorpay',
                        'payment_details': payment_entity,
                        'order_id': order_id,
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    # Only add user_id if we found one
                    if user_id:
                        payment_data['user_id'] = user_id
                    
                    logger.info(f"Processing payment with data: {payment_data}")
                    
                    if existing_payment.data:
                        result = supabase.table('payments')\
                            .update(payment_data)\
                            .eq('razorpay_payment_id', payment_id)\
                            .execute()
                        logger.info(f"Payment updated: {payment_id}")
                    else:
                        result = supabase.table('payments')\
                            .insert(payment_data)\
                            .execute()
                        logger.info(f"New payment created: {payment_id}")
                    
                    return JSONResponse(
                        status_code=200,
                        content={"status": "success", "payment_id": payment_id}
                    )
        
        return JSONResponse(status_code=200, content={"status": "success"})
                    
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

def handle_webhook_error(e: Exception) -> JSONResponse:
    error_message = str(e)
    if "ValidationError" in error_message:
        logger.warning(f"Received unhandled webhook event: {error_message}")
        return JSONResponse(
            status_code=200,  # Return 200 for unhandled events
            content={
                "status": "success",
                "message": "Unhandled webhook event acknowledged"
            }
        )
    
    logger.error(f"Webhook processing failed: {error_message}")
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": error_message
        }
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "webhook_url": RAZORPAY_CALLBACK_URL,
        "environment": "production"
    }

@app.post("/api/create-user")
async def create_user(user: UserCreate):
    try:
        # 1. Insert into users table
        if user.userId:
            users_result = supabase.table('users').insert({
                'id': user.userId,
                'email': user.email,
                'full_name': user.name,
                'username': user.email.split('@')[0]
            }).execute()

            if not users_result.data:
                logger.warning(f"Failed to create user record for: {user.email}")

            # 2. Insert into profiles table
            profiles_result = supabase.table('profiles').insert({
                'id': user.userId,
                'username': user.email.split('@')[0],  # Using email prefix as username
                'full_name': user.name
            }).execute()

            if not profiles_result.data:
                logger.warning(f"Failed to create profile for: {user.email}")

        # 3. Create user interaction
        result = supabase.table('user_interactions').insert({
            'email': user.email,
            'name': user.name,
            'phone_number': user.phone,
            'health_conditions': user.healthConditions or '',
            'interest': 'Free Weekend Class',
            'source': 'get_started',
            'account_created': True
        }).execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create user interaction")

        logger.info(f"User created successfully: {user.email}")
        return {"status": "success", "message": "User created successfully"}

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/signup")
async def create_auth_user(user_data: dict):
    try:
        source = user_data.get("source", "signup")
        
        # Choose template and redirect URL based on source
        if source in ["free_class", "sticky_header", "get_started"]:
            email_template = "reset_password"  # Matches exactly with Supabase template name
            redirect_to = f"{FRONTEND_URL}/reset-password"
        else:
            email_template = "confirm_signup"  # Matches exactly with Supabase template name
            redirect_to = f"{FRONTEND_URL}/auth"
        
        # Create auth user with correct template parameter
        auth_response = supabase.auth.sign_up({
            "email": user_data["email"],
            "password": user_data.get("password") or secrets.token_urlsafe(8),
            "options": {
                "data": {
                    "full_name": user_data["name"],
                    "phone": user_data.get("phone"),
                    "healthConditions": user_data.get("healthConditions"),
                    "interest": user_data.get("interest"),
                    "source": source
                },
                "email_redirect_to": redirect_to,
                "email_template": email_template  # Changed back to email_template
            }
        })

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to create auth user")

        # Create user in database tables
        await create_user(UserCreate(
            userId=auth_response.user.id,
            email=user_data["email"],
            name=user_data["name"],
            phone=user_data.get("phone"),
            healthConditions=user_data.get("healthConditions"),
            interest=user_data.get("interest"),
            source=source
        ))

        return {
            "status": "success",
            "userId": auth_response.user.id,
            "message": "User created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating auth user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])