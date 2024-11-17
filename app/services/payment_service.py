from typing import Dict, Any
from app.services.supabase_service import supabase
import logging
from datetime import datetime, timedelta

from app.config import PAISE_TO_RUPEE_CONVERSION, CURRENCY_CONFIGS

logger = logging.getLogger(__name__)

async def process_payment_event(event: str, payment_details: Dict[str, Any]):
    """Process different payment events and update database accordingly"""
    try:
        if not payment_details.get('razorpay_payment_id'):
            raise ValueError("Payment ID not found in webhook data")

        # Update/Insert payment record
        payment_record = await update_payment_record(payment_details)
        
        # Log success based on event type
        if event == 'payment.captured':
            logger.info(f"Payment successful for ID: {payment_details['razorpay_payment_id']}")
        elif event == 'payment.failed':
            logger.warning(f"Payment failed for ID: {payment_details['razorpay_payment_id']}")
        elif event == 'payment.pending':
            logger.info(f"Payment pending for ID: {payment_details['razorpay_payment_id']}")
            
        logger.info(f"Successfully processed {event} for payment {payment_details['razorpay_payment_id']}")
        
    except Exception as e:
        logger.error(f"Error processing payment event: {str(e)}")
        raise

async def update_payment_record(payment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Update or insert payment record in database"""
    try:
        logger.info(f"Attempting to update payment record: {payment_details}")
        
        # Convert amount from smallest unit to main currency unit
        if payment_details.get('amount') and payment_details.get('currency'):
            currency = payment_details['currency']
            amount = float(payment_details['amount'])
            
            # Convert from smallest unit (paise/cents) to main unit (rupees/dollars/euros)
            if currency == 'INR':
                payment_details['amount'] = amount / PAISE_TO_RUPEE_CONVERSION
            elif currency in ['USD', 'EUR']:
                payment_details['amount'] = amount / 100  # Convert cents to dollars/euros
                
        result = supabase.table('payments').upsert(
            payment_details,
            on_conflict='razorpay_payment_id'
        ).execute()
        
        if not result.data:
            logger.error("No data returned from payment record update")
            raise Exception("Failed to update payment record")
            
        logger.info(f"Payment record updated successfully: {result.data[0]}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error updating payment record: {str(e)}")
        raise