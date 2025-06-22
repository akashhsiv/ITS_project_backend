from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Business
from .serializers import BusinessSerializer, DeviceVerificationSerializer, ResetDeviceSerializer
from .email_utils import send_activation_email, send_welcome_email
import random
import string
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

def generate_key(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer

    def perform_create(self, serializer):
        # Generate credentials
        device_key = generate_key("DC", 8)
        user_id = generate_key("UZ", 6)
        pin = str(random.randint(1000, 9999))

        business = serializer.save(
            device_key=device_key,
            user_id=user_id,
            pin=pin,
            is_active=False
        )

        # Send activation email with the request context for URL building
        send_activation_email(business, self.request)

    def destroy(self, request, *args, **kwargs):
        business = self.get_object()
        business_name = business.business_name
        self.perform_destroy(business)
        return Response(
            {"message": f"Business '{business_name}' has been deleted."},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['post'], url_path='verify-device')
    def verify_device(self, request):
        """
        Verify device key and PIN for authentication
        """
        serializer = DeviceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        business = serializer.validated_data['business']
        
        # Here you can add additional logic like generating a token if needed
        # For now, we'll just return a success response with basic business info
        return Response({
            'success': True,
            'message': 'Device verified successfully',
            'business_id': business.id,
            'business_name': business.business_name,
            'user_id': business.user_id,
            'email': business.email
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='activate_device', serializer_class=DeviceVerificationSerializer)
    def activate_device(self, request):
        """
        Activate device with credentials
        Expected payload: {
            "device_registration_key": "DC123456",  # Required
            "pin": "1234"                          # Required
        }
        """
        serializer = DeviceVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        device_key = serializer.validated_data['device_key']
        pin = serializer.validated_data['pin']

        try:
            business = Business.objects.get(device_key=device_key, pin=pin)
            
            return Response({
                'success': True,
                'message': 'Device credentials verified successfully',
                'email': business.email,
                'business_name': business.business_name,
                'device_registration_key': business.device_key,  # Changed from device_key
                'user_id': business.user_id,
                'pin': business.pin
            })

        except Business.DoesNotExist:
            return Response(
                {'error': 'Invalid device key or pin'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='reset_device', serializer_class=ResetDeviceSerializer)
    def reset_device(self, request):
        """
        Reset device credentials and resend welcome email
        Expected payload: {
            "account_number": 12345678,  # Required
            "email": "user@example.com"   # Required
        }
        """
        
        serializer = ResetDeviceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        business = serializer.validated_data['business']
        
        try:
            # Resend the welcome email with existing credentials
            send_welcome_email(business, request)
            
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



# from rest_framework import status, viewsets
# from rest_framework.response import Response
# from rest_framework.decorators import action
# from .models import Business
# from .serializers import (
#     BusinessSerializer,
#     BusinessNameSerializer,
#     BusinessAddressSerializer,
#     BusinessTypeSerializer,
#     PrimaryContactSerializer
# )

# class BusinessViewSet(viewsets.ModelViewSet):
#     queryset = Business.objects.all()
#     serializer_class = BusinessSerializer

    # @action(detail=False, methods=['post'], url_path='initialize')
    # def initialize_business(self, request):
    #     serializer = BusinessNameSerializer(data=request.data)
    #     if serializer.is_valid():
    #         business = serializer.save()
    #         return Response({'id': business.id, **serializer.data}, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['put'], url_path='address')
#     def update_address(self, request, pk=None):
#         business = self.get_object()
#         serializer = BusinessAddressSerializer(business, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({'message': 'Address updated successfully'})
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['put'], url_path='type')
#     def update_type(self, request, pk=None):
#         business = self.get_object()
#         serializer = BusinessTypeSerializer(business, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({'message': 'Business type updated successfully'})
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['put'], url_path='primary-contact')
#     def update_primary_contact(self, request, pk=None):
#         business = self.get_object()
#         serializer = PrimaryContactSerializer(business, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({'message': 'Primary contact updated successfully'})
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


import logging
logger = logging.getLogger(__name__)

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
                logger.error(f"Token validation failed for business: {business.id}")
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
                    send_welcome_email(business, request)
                    logger.info(f"Welcome email sent to: {business.email}")
                except Exception as email_error:
                    logger.error(f"Error sending welcome email: {str(email_error)}")
                    # Don't fail activation if email fails
                
                return Response({
                    'success': True,
                    'message': 'Your account has been successfully activated. Please check your email for your login credentials.'
                })
                
            except Exception as activation_error:
                logger.error(f"Error during account activation: {str(activation_error)}")
                raise activation_error
            
        except Exception as e:
            logger.error(f"Unexpected error in BusinessActivationView: {str(e)}", exc_info=True)
            return Response(
                {'error': f'An error occurred while activating your account: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

