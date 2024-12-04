import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

def setup_logging():
    """Configure logging with security and rotation"""
    log_level = logging.WARNING if os.getenv('ENVIRONMENT', 'production') == 'production' else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Setup rotating file handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10000000,  # 10MB
        backupCount=5
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    
    # Common formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('app.main').setLevel(log_level)
    logging.getLogger('app.services').setLevel(log_level)
    
    # Disable propagation of sensitive loggers
    logging.getLogger('supabase').propagate = False
    logging.getLogger('razorpay').propagate = False

# Load environment variables
load_dotenv()

# Environment setup
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
DEBUG = ENVIRONMENT == 'development'
IS_DEVELOPMENT = DEBUG

# Initialize logging
setup_logging()

# Log startup without sensitive data
logger = logging.getLogger(__name__)
logger.info(f"Application starting in {ENVIRONMENT} mode")

# Use actual domain in production
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.yogforever.com')
RAZORPAY_CALLBACK_URL = f"{API_BASE_URL}/razorpay-webhook"

# Supabase credentials (existing setup)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # Use anon key

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
if not API_BASE_URL:
    raise ValueError("API_BASE_URL must be set in the environment variables")

# Remove sensitive URL logging
logger.info("API and callback URLs configured successfully")

# Payment status mapping
PAYMENT_STATUS_MAP = {
    'created': 'pending',
    'authorized': 'processing',
    'captured': 'completed',
    'failed': 'failed',
    'refunded': 'refunded'
}

# Add amount conversion constant
PAISE_TO_RUPEE_CONVERSION = 100

# Add FRONTEND_URL and AUTH_REDIRECT_URL
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://yogforever.com')
AUTH_REDIRECT_URL = f"{FRONTEND_URL}/auth?tab=signin"
RESET_PASSWORD_URL = f"{FRONTEND_URL}/reset-password"
VERIFY_EMAIL_URL = f"{FRONTEND_URL}/auth"  # New URL for email verification

# Remove localhost fallback
if not FRONTEND_URL:
    FRONTEND_URL = 'https://yogforever.com'
    
if not AUTH_REDIRECT_URL:
    AUTH_REDIRECT_URL = 'https://yogforever.com/auth'

logger.info(f"[CONFIG] FRONTEND_URL set to: {FRONTEND_URL}")
logger.info(f"[CONFIG] AUTH_REDIRECT_URL set to: {AUTH_REDIRECT_URL}")

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
