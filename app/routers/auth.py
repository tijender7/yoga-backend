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
        logger.debug(f"Checking email: {data.email}")
        logger.debug(f"Using Supabase URL: {SUPABASE_URL}")
        
        # Add more debug info
        logger.debug("Attempting to list users with admin privileges")
        result = supabase.auth.admin.list_users()
        
        if not result or not hasattr(result, 'users'):
            logger.error("Invalid response from Supabase")
            raise HTTPException(status_code=500, detail="Invalid response from auth service")
            
        emails = [user.email for user in result.users]
        return {
            "exists": data.email in emails,
            "message": "Email check completed"
        }
    except Exception as e:
        logger.error(f"Error checking email: {str(e)}", exc_info=True)
        if "User not allowed" in str(e):
            raise HTTPException(
                status_code=401, 
                detail="Authentication failed - check Supabase service role key"
            )
        raise HTTPException(status_code=500, detail=str(e))