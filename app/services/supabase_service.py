# backend/app/services/supabase_service.py
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Supabase credentials must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)