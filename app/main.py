from fastapi import FastAPI, HTTPException, Request
from app.services.razorpay_service import create_payment_link
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import AUTH_REDIRECT_URL, FRONTEND_URL, IS_DEVELOPMENT, PAYMENT_STATUS_MAP, RAZORPAY_CALLBACK_URL, RESET_PASSWORD_URL, VERIFY_EMAIL_URL
from datetime import datetime
from app.services.supabase_service import supabase
from fastapi.responses import JSONResponse
from typing import Dict, Any
from pydantic import BaseModel, Field
from typing import Optional
from pydantic import EmailStr
import secrets
import os
from app.routers import auth, webhook

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
        logger.info(f"Processing signup request - Source: {source}")
        
        is_form_signup = source in ['free_class', 'contact', 'get_started', 'sticky_header']
        temp_password = ''
        
        if is_form_signup:
            temp_password = secrets.token_urlsafe(12)
            logger.info(f"Generated temp password for form signup: {user_data['email']}")
            
            # For form signup: Create user with email already confirmed
            auth_response = supabase.auth.sign_up({
                "email": user_data["email"],
                "password": temp_password,
                "options": {
                    "data": {
                        "full_name": user_data["name"],
                        "phone": user_data.get("phone"),
                        "healthConditions": user_data.get("healthConditions"),
                        "source": source
                    },
                    "email_confirm": True,  # Auto confirm email
                    "suppress_email": True   # Don't send confirmation email
                }
            })
            
            # Send only password reset email
            if auth_response.user:
                try:
                    reset_response = supabase.auth.reset_password_for_email(
                        user_data["email"],
                        options={
                            "redirect_to": RESET_PASSWORD_URL
                        }
                    )
                    logger.info(f"Password reset email sent for form signup: {user_data['email']}")
                except Exception as e:
                    logger.error(f"Failed to send password reset email: {str(e)}")
                    pass
                    
        else:
            # Direct signup: Normal flow with email verification
            temp_password = user_data.get("password")
            if not temp_password:
                raise HTTPException(status_code=400, detail="Password required for direct signup")
                
            auth_response = supabase.auth.sign_up({
                "email": user_data["email"],
                "password": temp_password,
                "options": {
                    "data": {
                        "full_name": user_data["name"],
                        "phone": user_data.get("phone"),
                        "healthConditions": user_data.get("healthConditions"),
                        "source": source
                    },
                    "email_confirm": False,
                    "redirect_to": AUTH_REDIRECT_URL
                }
            })

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to create auth user")

        # Create user in database
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
app.include_router(webhook.router)