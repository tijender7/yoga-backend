from fastapi import APIRouter, HTTPException
from app.models.auth import EmailCheck
from app.services.supabase_service import supabase
import logging
from app.utils.logging_utils import mask_email, get_error_code

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/check-email")
async def check_email_exists(data: EmailCheck):
    try:
        # Log with masked email
        masked = mask_email(data.email)
        logger.debug(f"Processing email check: {masked}")
        
        # Use public users table instead of admin API
        result = supabase.table('users') \
            .select('email') \
            .eq('email', data.email) \
            .execute()
            
        exists = len(result.data) > 0
        
        # Log result without exposing email
        logger.debug(f"Email check completed: {'exists' if exists else 'not found'}")
        
        return {
            "exists": exists,
            "message": "Email check completed"
        }
    except Exception as e:
        # Log error with code but without sensitive data
        error_code = get_error_code(e)
        logger.error(f"Email check failed: {error_code}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to process email check"
        )