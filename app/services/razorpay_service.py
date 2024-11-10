import razorpay
from app.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_CALLBACK_URL
import logging

logger = logging.getLogger(__name__)
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

SUPPORTED_CURRENCIES = ['INR', 'USD', 'EUR']

async def create_payment_link(amount: int, currency: str = 'INR', description: str = '', user_id: str = None):
    try:
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Currency {currency} not supported. Supported currencies: {SUPPORTED_CURRENCIES}")
            
        # Convert amount to lowest denomination based on currency
        if currency == 'INR':
            amount = int(amount)  # Already in paise from frontend
        else:
            # For USD and EUR, amount comes in cents from frontend
            # No need to multiply by 100 again
            amount = int(amount)
            
        payment_data = {
            "amount": amount,
            "currency": currency,
            "accept_partial": False,
            "description": description,
            "callback_url": RAZORPAY_CALLBACK_URL,
            "callback_method": "post",
            "notes": {
                "user_id": user_id
            } if user_id else {}
        }
        
        logger.info(f"Creating payment link with data: {payment_data}")
        payment_link = client.payment_link.create(payment_data)
        return payment_link['short_url']
    except Exception as e:
        logger.error(f"Payment link creation failed: {str(e)}")
        raise
