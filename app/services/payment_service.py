from typing import Dict, Any
from app.services.supabase_service import supabase
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def process_payment_event(event: str, payment_details: Dict[str, Any]):
    """Process different payment events and update database accordingly"""
    try:
        if not payment_details.get('razorpay_payment_id'):
            raise ValueError("Payment ID not found in webhook data")

        # Update/Insert payment record
        payment_record = await update_payment_record(payment_details)
        
        # Handle specific payment events
        if event == 'payment.captured':
            await handle_successful_payment(payment_record)
        elif event == 'payment.failed':
            await handle_failed_payment(payment_record)
        elif event == 'payment.pending':
            await handle_pending_payment(payment_record)
            
        logger.info(f"Successfully processed {event} for payment {payment_details['razorpay_payment_id']}")
        
    except Exception as e:
        logger.error(f"Error processing payment event: {str(e)}")
        raise

async def update_payment_record(payment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Update or insert payment record in database"""
    try:
        logger.info(f"Attempting to update payment record: {payment_details}")
        result = await supabase.table('payments').upsert(
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

async def handle_successful_payment(payment_record: Dict[str, Any]):
    """Handle successful payment completion"""
    try:
        user_id = payment_record.get('user_id')
        if not user_id:
            logger.warning("User ID not found in payment record")
            return
            
        # Create or update subscription
        subscription_data = {
            'user_id': user_id,
            'status': 'active',
            'payment_id': payment_record['razorpay_payment_id'],
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=30),  # 30 days subscription
            'payment_method': payment_record['payment_method']
        }
        
        result = await supabase.table('subscriptions').insert(subscription_data).execute()
        
        if not result.data:
            raise Exception("Failed to create subscription record")
            
        logger.info(f"Created subscription for user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling successful payment: {str(e)}")
        raise

async def handle_failed_payment(payment_record: Dict[str, Any]):
    """Handle failed payment"""
    try:
        user_id = payment_record.get('user_id')
        if user_id:
            # Log failed payment attempt
            await supabase.table('payment_failures').insert({
                'user_id': user_id,
                'payment_id': payment_record['razorpay_payment_id'],
                'failure_reason': payment_record.get('payment_details', {}).get('error_description', 'Unknown error'),
                'created_at': datetime.now()
            }).execute()
            
        logger.warning(f"Payment failed for ID: {payment_record['razorpay_payment_id']}")
        
    except Exception as e:
        logger.error(f"Error handling failed payment: {str(e)}")
        raise

async def handle_pending_payment(payment_record: Dict[str, Any]):
    """Handle pending payment status"""
    logger.info(f"Payment pending for ID: {payment_record['razorpay_payment_id']}")