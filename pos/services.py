from django.conf import settings
import razorpay
from rest_framework.exceptions import ValidationError
from rest_framework import status

def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class RazorpayClient:
    def __init__(self):
        self.client = get_razorpay_client()

    def create_order(self, amount, currency):
        data = {
            "amount": amount,
            "currency": currency,
        }
        try:
            order_data = self.client.order.create(data=data)
            return order_data
        except Exception as e:
            raise ValidationError(
                {
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": str(e)
                }
            )

    def verify_payment(self, razorpay_payment_id, razorpay_order_id, razorpay_signature):
        try:
            return self.client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
        except Exception as e:
            raise ValidationError(
                {
                    'status_code': status.HTTP_400_BAD_REQUEST,
                    'message': str(e)
                }
            )