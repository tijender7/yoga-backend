from fastapi import APIRouter, HTTPException
from app.models.auth import EmailCheck
from app.services.supabase_service import supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/check-email")
async def check_email_exists(data: EmailCheck):
    try:
        logger.debug(f"Checking email: {data.email}")
        
        # Use public users table instead of admin API
        result = supabase.table('users') \
            .select('email') \
            .eq('email', data.email) \
            .execute()
            
        exists = len(result.data) > 0
        
        return {
            "exists": exists,
            "message": "Email check completed"
        }
    except Exception as e:
        logger.error(f"Error checking email: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to check email: {str(e)}"
        )