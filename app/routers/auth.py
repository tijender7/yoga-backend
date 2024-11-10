from fastapi import APIRouter, HTTPException
from app.models.auth import EmailCheck
from app.services.supabase_service import supabase
from app.config import SUPABASE_URL, SUPABASE_KEY
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/check-email")
async def check_email_exists(data: EmailCheck):
    try:
        # Add debug logging
        logger.debug(f"Checking email: {data.email}")
        logger.debug(f"Supabase URL: {SUPABASE_URL}")
        
        # Use auth.users to check if email exists
        result = supabase.auth.admin.list_users()
        logger.debug(f"Supabase response: {result}")
        
        emails = [user.email for user in result.users]
        return {
            "exists": data.email in emails,
            "message": "Email check completed"
        }
    except Exception as e:
        # More detailed error logging
        logger.error(f"Error checking email: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to check email: {str(e)}"
        )