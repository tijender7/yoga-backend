from fastapi import APIRouter, HTTPException
from models.auth import EmailCheck
from services.supabase_service import supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/check-email")
async def check_email_exists(data: EmailCheck):
    try:
        # Use auth.users to check if email exists
        result = supabase.auth.admin.list_users()
        emails = [user.email for user in result.users]
        
        return {
            "exists": data.email in emails,
            "message": "Email check completed"
        }
    except Exception as e:
        logger.error(f"Error checking email: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check email")