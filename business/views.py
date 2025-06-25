
import logging
import random
import string

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Business
from datetime import timedelta
from django.utils import timezone

from .serializers import BusinessLoginSerializer, BusinessSerializer, DeviceVerificationSerializer, ForgotPinSerializer, ResetDeviceSerializer
from .email_utils import send_activation_email, send_forgot_pin_email, send_new_pin_email, send_request_registration_key_email, send_welcome_email


logger = logging.getLogger(__name__)


def generate_key(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer

    def perform_create(self, serializer):
        account_number = str(random.randint(10000000, 99999999))
        device_key = generate_key("DC", 8)
        user_id = generate_key("ITS", 6)
        pin = str(random.randint(1000, 9999))

        business = serializer.save(
            account_number=account_number,
            device_key=device_key,
            user_id=user_id,
            pin=pin,
            is_active=False
        )

        # Send activation email
        send_activation_email(business, self.request)

    def destroy(self, request, *args, **kwargs):
        business = self.get_object()
        business_name = business.business_name
        self.perform_destroy(business)
        return Response(
            {"message": f"Business '{business_name}' has been deleted."},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['post'], url_path='register_device', serializer_class=DeviceVerificationSerializer)
    def register_device(self, request):
        """
        Register device with credentials
        Expected payload: 
        {
            "device_registration_key": "DC123456",  
            "pin": "1234"                          
        }
        """
        serializer = DeviceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        device_key = serializer.validated_data['device_key']
        device_label = serializer.validated_data['device_label']

        try:
            business = Business.objects.get(device_key=device_key)
            business.device_label = device_label
            business.save(update_fields=["device_label"])

            return Response({
                'success': True,
                'message': 'Device credentials registered successfully',
                'email': business.email,
                'business_name': business.business_name,
                'device_registration_key': business.device_key,
                'device_label': business.device_label,
                'user_id': business.user_id,
                'pin': business.pin
            })

        except Business.DoesNotExist:
            return Response(
                {'error': 'Invalid device key or pin'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='request_device_registration_key', serializer_class=ResetDeviceSerializer)
    def request_device_registration_key(self, request):

        serializer = ResetDeviceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        business = serializer.validated_data['business']
        new_device_key = generate_key("DC", 8)

        business.device_key = new_device_key
        business.device_key_expires = new_expiry
        business.save(update_fields=["device_key"])

        try:
            # Resend the welcome email with existing credentials
            send_request_registration_key_email(business)

            return Response({
                'success': True,
                'message': 'Device credentials have been sent to your email',
                'email': business.email
            })

        except Exception as e:
            return Response(
                {'error': 'Failed to send device credentials. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="forgot_pin", serializer_class= ForgotPinSerializer)
    def forgot_pin_request(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=400)

        try:
            business = Business.objects.get(email=email)
            # generate a unique link (e.g., containing UUID or token)
            # Here just using activation token again (or add separate one if you prefer)
            token = business.generate_forgot_pin_token()
            reset_url = request.build_absolute_uri(
                f"/api/forgot_pin/confirm/{token}/")
            send_forgot_pin_email(business, reset_url)
            return Response({"message": "A reset pin link has been sent to your email."})
        except Business.DoesNotExist:
            return Response({"error": "Business not found."}, status=404)

    @action(detail=False, methods=['post'], url_path='login_with_pin', serializer_class=BusinessLoginSerializer)
    def login_with_pin(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            business = serializer.validated_data['business']
            return Response({
                'success': True,
                'message': 'Login successful',
                'business_name': business.business_name,
                'email': business.email,
                'user_id': business.user_id,
                'pin': business.pin,
                'device_key': business.device_key,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPinConfirmView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            business = Business.objects.get(forgot_pin_token=token)

            if not business.is_forgot_pin_token_valid():
                return Response({"error": "Token expired or invalid."}, status=400)

            new_pin = str(random.randint(1000, 9999))
            business.pin = new_pin
            business.forgot_pin_token = None
            business.forgot_pin_token_expires = None
            business.save(
                update_fields=["pin", "forgot_pin_token", "forgot_pin_token_expires"])

            send_new_pin_email(business, new_pin)
            return Response({"message": "A new PIN has been sent to your email."})
        except Business.DoesNotExist:
            return Response({"error": "Invalid token."}, status=404)


class BusinessActivationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            logger.info(f"Attempting to activate account with token: {token}")

            # Try to find a business with the given activation token
            try:
                business = Business.objects.get(
                    activation_token=token,
                    is_active=False
                )
                logger.info(f"Found business: {business.business_name}")
            except Business.DoesNotExist:
                logger.error(f"No business found with token: {token}")
                return Response(
                    {'error': 'Invalid activation link. The link may have expired or already been used.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if token is valid and not expired
            if not business.is_activation_token_valid():
                logger.error(
                    f"Token validation failed for business: {business.id}")
                return Response(
                    {'error': 'Activation link has expired or is invalid. Please request a new activation link.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Activate the business account
            try:
                business.activate_account()
                logger.info(f"Successfully activated business: {business.id}")

                # Send welcome email with credentials
                try:
                    send_welcome_email(business)
                    logger.info(f"Welcome email sent to: {business.email}")
                except Exception as email_error:
                    logger.error(
                        f"Error sending welcome email: {str(email_error)}")
                    # Don't fail activation if email fails

                return Response({
                    'success': True,
                    'message': 'Your account has been successfully activated. Please check your email for your login credentials.'
                })

            except Exception as activation_error:
                logger.error(
                    f"Error during account activation: {str(activation_error)}")
                raise activation_error

        except Exception as e:
            logger.error(
                f"Unexpected error in BusinessActivationView: {str(e)}", exc_info=True)
            return Response(
                {'error': f'An error occurred while activating your account: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
