import os
import logging
from dotenv import load_dotenv
# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to INFO or DEBUG based on your needs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Optionally, set levels for specific loggers
logging.getLogger('app.main').setLevel(logging.DEBUG)
logging.getLogger('app.services').setLevel(logging.INFO)

# Load environment variables from .env
load_dotenv()



# config.py mein ya main file ke top par
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
DEBUG = ENVIRONMENT == 'development'

print(f"ENVIRONMENT: {ENVIRONMENT}")  # Debug ke liye
print(f"IS_DEVELOPMENT: {DEBUG}")  # Debug ke liye

logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='production.log' if not DEBUG else None
)

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
NGROK_URL = os.getenv("NGROK_URL")
if not NGROK_URL:
    raise ValueError("NGROK_URL must be set in the environment variables")
RAZORPAY_CALLBACK_URL = f"{NGROK_URL}/razorpay-webhook"

# Supabase credentials (existing setup)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# Razorpay credentials
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# Add this check
if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or not RAZORPAY_WEBHOOK_SECRET:
    raise ValueError("Razorpay credentials (KEY_ID, KEY_SECRET, and WEBHOOK_SECRET) must be set in the environment variables")

# Add this after loading environment variables
logger = logging.getLogger(__name__)
logger.info("Payment gateway configuration loaded successfully")

# Validation add karein
if not NGROK_URL:
    raise ValueError("NGROK_URL must be set in the environment variables")

logger.info(f"[CONFIG] NGROK_URL set to: {NGROK_URL}")
logger.info(f"[CONFIG] RAZORPAY_CALLBACK_URL set to: {RAZORPAY_CALLBACK_URL}")

# Payment status mapping
PAYMENT_STATUS_MAP = {
    'created': 'pending',
    'authorized': 'processing',
    'captured': 'completed',
    'failed': 'failed',
    'refunded': 'refunded'
}

# Add FRONTEND_URL to our config
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Currency configuration
CURRENCY_CONFIGS = {
    'INR': {
        'symbol': '₹',
        'decimal_places': 2,
        'min_amount': 100,  # 1 INR in paise
    },
    'USD': {
        'symbol': '$',
        'decimal_places': 2,
        'min_amount': 50,   # 0.50 USD in cents
    },
    'EUR': {
        'symbol': '€',
        'decimal_places': 2,
        'min_amount': 50,   # 0.50 EUR in cents
    }
}
