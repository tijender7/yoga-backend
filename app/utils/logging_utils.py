"""Utility functions for secure logging"""
import re
from typing import Any, Dict, Union

def mask_email(email: str) -> str:
    """Mask email address while preserving format
    Example: test@example.com -> te**@ex***le.com
    """
    if not email or '@' not in email:
        return '***'
    
    username, domain = email.split('@')
    domain_parts = domain.split('.')
    
    # Mask username
    masked_username = username[:2] + '*' * (len(username) - 2)
    
    # Mask domain
    masked_domain = domain_parts[0][:2] + '*' * (len(domain_parts[0]) - 2)
    
    return f"{masked_username}@{masked_domain}.{domain_parts[-1]}"

def mask_payment_id(payment_id: str) -> str:
    """Mask payment ID while preserving format
    Example: pay_123456789 -> pay_***6789
    """
    if not payment_id:
        return '***'
    
    # Keep prefix and last 4 chars
    prefix = payment_id.split('_')[0] if '_' in payment_id else payment_id[:3]
    return f"{prefix}_***{payment_id[-4:]}"

def mask_sensitive_data(data: Union[Dict, str, None]) -> Union[Dict, str, None]:
    """Mask sensitive information in dictionaries or strings"""
    if data is None:
        return None
        
    if isinstance(data, str):
        # Check if it's an email
        if '@' in data and '.' in data:
            return mask_email(data)
        # Check if it's a payment ID
        if data.startswith(('pay_', 'order_', 'txn_')):
            return mask_payment_id(data)
        return data
        
    if isinstance(data, dict):
        masked_data = data.copy()
        sensitive_fields = {
            'email': mask_email,
            'payment_id': mask_payment_id,
            'razorpay_payment_id': mask_payment_id,
            'order_id': mask_payment_id,
            'password': lambda x: '***',
            'token': lambda x: '***',
            'api_key': lambda x: '***',
        }
        
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                masked_data[key] = sensitive_fields[key.lower()](value)
            elif isinstance(value, (dict, str)):
                masked_data[key] = mask_sensitive_data(value)
                
        return masked_data
        
    return data

def get_error_code(error: Exception) -> str:
    """Extract error code or create generic one without sensitive details"""
    error_str = str(error)
    
    # Common error patterns
    patterns = {
        'database': r'(database|db|sql)',
        'network': r'(network|connection|timeout)',
        'validation': r'(invalid|validation)',
        'auth': r'(auth|unauthorized|forbidden)',
        'payment': r'(payment|transaction)',
    }
    
    for category, pattern in patterns.items():
        if re.search(pattern, error_str.lower()):
            return f"{category}_error"
            
    return "general_error" 