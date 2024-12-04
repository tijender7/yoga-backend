from typing import Dict, Any
from app.services.supabase_service import supabase
import logging
from datetime import datetime, timedelta
from app.utils.logging_utils import mask_sensitive_data, mask_payment_id
from app.config import PAISE_TO_RUPEE_CONVERSION, CURRENCY_CONFIGS

logger = logging.getLogger(__name__)

async def process_payment_event(event: str, payment_details: Dict[str, Any]):
    """Process different payment events and update database accordingly"""
    try:
        # Skip payment ID check for downtime events
        if 'downtime' in event:
            logger.info(f"Processing maintenance event: {event}")
            return
            
        if not payment_details.get('razorpay_payment_id'):
            raise ValueError("Payment ID not found in webhook data")

        # Mask payment details for logging
        masked_details = mask_sensitive_data(payment_details)
        payment_id = mask_payment_id(payment_details.get('razorpay_payment_id', ''))

        # Update/Insert payment record
        payment_record = await update_payment_record(payment_details)
        
        # Log success based on event type with masked data
        if event == 'payment.captured':
            logger.info(f"Payment successful - ID: {payment_id}")
        elif event == 'payment.failed':
            logger.warning(f"Payment failed - ID: {payment_id}")
        elif event == 'payment.pending':
            logger.info(f"Payment pending - ID: {payment_id}")
            
        logger.info(f"Event processed: {event} - Payment ID: {payment_id}")
        
    except Exception as e:
        # Log error without exposing payment details
        logger.error(f"Payment processing error: {type(e).__name__}")
        raise

async def update_payment_record(payment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Update or insert payment record in database"""
    try:
        # Mask payment details for logging
        masked_details = mask_sensitive_data(payment_details)
        logger.info("Updating payment record")
        
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

async def is_duplicate_event(event_id: str) -> bool:
    """Check if event has already been processed"""
    try:
        result = await supabase.table('webhook_events').select('id').eq('event_id', event_id).execute()
        return bool(result.data)
    except Exception as e:
        logger.error(f"Error checking duplicate event: {str(e)}")
        return False

async def store_webhook_event(event_id: str, event_type: str, payload: dict):
    """Store webhook event for idempotency"""
    try:
        await supabase.table('webhook_events').insert({
            'event_id': event_id,
            'event_type': event_type,
            'payload': payload,
            'processed_at': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Error storing webhook event: {str(e)}")