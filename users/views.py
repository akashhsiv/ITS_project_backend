import logging
import random
import string
import bcrypt
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import PINLoginSerializer, UserCreateSerializer
from .emai_utils import send_activation_email, send_welcome_email

logger = logging.getLogger(__name__)


def generate_user_id(prefix="USR", length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_pin(length=4):
    return ''.join(random.choices(string.digits, k=length))


class UserActivationView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        try:
            user = get_object_or_404(User, activation_token=token, is_active=False)
            
            if not user.is_activation_token_valid():
                return Response(
                    {'error': 'Activation link has expired. Please request a new one.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Activate the user
            user.activate_account()
            
            # Generate a temporary PIN for first login
            raw_pin = generate_pin()
            user.pin_hash = bcrypt.hashpw(raw_pin.encode(), bcrypt.gensalt()).decode()
            user.pin_plaintext = raw_pin  # Temporary storage for email
            user.save(update_fields=['pin_hash', 'pin_plaintext'])
            
            # Send welcome email with credentials
            send_welcome_email(user, raw_pin)
            
            return Response(
                {'message': 'Account activated successfully. Please check your email for login credentials.'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error activating user account: {str(e)}")
            return Response(
                {'error': 'An error occurred while activating your account. Please contact support.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserCreateAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Auto-generate user_id
        user_id = generate_user_id()
        
        # Generate a temporary PIN that will be set after activation
        raw_pin = generate_pin()
        hashed_pin = bcrypt.hashpw(raw_pin.encode(), bcrypt.gensalt()).decode()

        # Inject values
        validated_data['user_id'] = user_id
        validated_data['pin_hash'] = hashed_pin
        validated_data['is_active'] = False  # User starts as inactive

        # Remove the raw pin if it's in input
        validated_data.pop('pin', None)
        
        # Create the user
        user = serializer.create(validated_data)
        
        try:
            # Send activation email
            send_activation_email(user, request)
            
            return Response(
                {
                    'message': 'User created successfully. Please check your email to activate your account.',
                    'user_id': user.user_id,
                    'email': user.email,
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            # If email sending fails, delete the user to avoid orphaned accounts
            user.delete()
            logger.error(f"Error sending activation email: {str(e)}")
            return Response(
                {'error': 'Failed to send activation email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Send email to user with credentials
            send_user_credentials_email(user, raw_pin)
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")

        return Response({
            "message": "User created successfully",
            "user_id": user.user_id,
            "pin": raw_pin  # optional: only show in dev
        }, status=status.HTTP_201_CREATED)


class PINLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PINLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']
        pin = serializer.validated_data['pin']

        try:
            user = User.objects.get(user_id=user_id)

            # Check if account is active
            if not user.is_active:
                return Response(
                    {'error': 'Account not activated. Please check your email for the activation link.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Verify PIN
            if not bcrypt.checkpw(pin.encode(), user.pin_hash.encode()):
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # Clear the plaintext PIN if it exists (should only be set during activation)
            if user.pin_plaintext:
                user.pin_plaintext = None
                user.save(update_fields=['pin_plaintext'])

            # Get or create token
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': {
                    'user_id': user.user_id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'role': user.role,
                    'business_id': str(user.business.id) if user.business else None,
                    'business_name': user.business.business_name if user.business else None,
                }
            })

        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
