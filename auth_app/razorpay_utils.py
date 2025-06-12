import razorpay
import os
import json
import hmac
import hashlib

# Razorpay credentials - Use hardcoded values directly for testing
RAZORPAY_KEY_ID = 'rzp_test_fCOl3SiLoZo5zJ'
RAZORPAY_KEY_SECRET = '4eQIh5B588ZeN6HFU2Svtrok'

# Initialize Razorpay client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(amount, currency="INR", receipt=None, notes=None):
    """
    Create a Razorpay order
    
    Args:
        amount (int): Amount in smallest currency unit (paise for INR)
        currency (str): Currency code (default: INR)
        receipt (str): Receipt ID
        notes (dict): Additional notes for the order
        
    Returns:
        dict: Order details including order_id
    """
    data = {
        'amount': amount,
        'currency': currency
    }
    
    if receipt:
        data['receipt'] = receipt
        
    if notes:
        data['notes'] = notes
        
    try:
        order = client.order.create(data=data)
        return order
    except Exception as e:
        print(f"Error creating Razorpay order: {str(e)}")
        raise

def verify_payment_signature(payment_id, order_id, signature):
    """
    Verify the Razorpay payment signature
    
    Args:
        payment_id (str): Razorpay payment ID
        order_id (str): Razorpay order ID
        signature (str): Razorpay signature
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # Generate the expected signature
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare with the provided signature
        return hmac.compare_digest(generated_signature, signature)
    except Exception as e:
        print(f"Error verifying Razorpay signature: {str(e)}")
        return False

def get_payment_details(payment_id):
    """
    Get payment details from Razorpay
    
    Args:
        payment_id (str): Razorpay payment ID
        
    Returns:
        dict: Payment details
    """
    try:
        payment = client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        print(f"Error fetching payment details: {str(e)}")
        raise
