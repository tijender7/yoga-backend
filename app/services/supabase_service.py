# backend/app/services/supabase_service.py
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY
import logging

logger = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
logger.info("Supabase client initialized successfully")