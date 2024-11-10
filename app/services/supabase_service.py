# backend/app/services/supabase_service.py
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY
import logging

logger = logging.getLogger(__name__)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise