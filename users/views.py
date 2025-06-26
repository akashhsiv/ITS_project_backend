import logging
import random
import string
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import mixins, status, viewsets
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .email_utils import send_new_pin_email, send_request_registration_key_email

from .models import User
from .serializers import ChangePinSerializer, DeviceVerificationSerializer, ForgotPinSerializer, ResetDeviceSerializer, UserIDTokenObtainPairSerializer, UserCreateSerializer, UserSerializer, generate_key
from .email_utils import send_activation_email, send_welcome_email, send_forgot_pin_email
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def generate_pin(length=4):
    return ''.join(random.choices(string.digits, k=length))


class LoginView(TokenObtainPairView):
    serializer_class = UserIDTokenObtainPairSerializer


class UserActivationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = get_object_or_404(
                User, activation_token=token, is_active=False)

            if not user.is_activation_token_valid():
                return Response(
                    {
                        "error": "Activation link is invalid or has expired. "
                        "Please request a new one."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                pin = user.activate_account()

            send_welcome_email(user, pin)

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


class UserViewSet(
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet):

    queryset = User.objects.all()
    permission_classes = [AllowAny]

    # choose serializer depending on action
    serializer_class = UserSerializer

    # Map each action to its own serializer
    serializer_action_classes = {
        "create": UserCreateSerializer,
        "register_device": DeviceVerificationSerializer,
        "request_device_registration_key": ResetDeviceSerializer,
        "change_pin": ChangePinSerializer,
    }

    def get_serializer_class(self):
        """
        Return the serializer class that should be used for the
        current action. Falls back to the view-wide `serializer_class`
        if the action is not in the map.
        """
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]
        return super().get_serializer_class()

    # custom create (POST /api/users/)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,
                                         context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        send_activation_email(user, request)

        return Response(
            {
                "message": (
                    "User created successfully. "
                    "Please check your email to activate your account."
                )
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="register_device",
            serializer_class=DeviceVerificationSerializer,
            permission_classes=[AllowAny])
    def register_device(self, request):
        """
        Register a device to a user.

        Expected JSON payload:
        {
          "device_registration_key": "DC123456",
          "pin": "1234",
          "device_label": "Cash-Counter Tablet"
        }
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        device_label = serializer.validated_data["device_label"]

        user.device_label = device_label
        user.save(update_fields=["device_label"])

        return Response(
            {
                "success": True,
                "message": "Device credentials registered successfully",
                "business_name": user.business.business_name,
                "email": user.contact.email,
                "device_registration_key": user.device_key,
                "device_label": user.device_label,
                "user_id": user.user_id,
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='request_device_registration_key', serializer_class=ResetDeviceSerializer)
    def request_device_registration_key(self, request):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        new_device_key = generate_key("DC", 8)
        user.device_key = new_device_key
        user.save(update_fields=["device_key"])

        try:
            # Resend the welcome email with existing credentials
            send_request_registration_key_email(user)
            return Response({
                'success': True,
                'message': 'Device credentials have been sent to your email',
                'email': user.contact.email
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="forgot_pin", serializer_class=ForgotPinSerializer)
    def forgot_pin_request(self, request):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        try:
            token = user.generate_forgot_pin_token()
            reset_url = request.build_absolute_uri(
                f"/api/forgot_pin/confirm/{token}/")
            send_forgot_pin_email(user, reset_url)
            return Response({"message": "A reset pin link has been sent to your email."})
        except User.DoesNotExist:
            return Response({"error": "Business not found."}, status=404)
        
    @action(detail=False, methods=["post"], url_path="change_pin",
            serializer_class=ChangePinSerializer,
            permission_classes=[IsAuthenticated])
    def change_pin(self, request):
        """
        Allows an authenticated user to change their PIN.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "PIN changed successfully."},
            status=status.HTTP_200_OK
        )


class ForgotPinConfirmView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, token):
        try:
            user = User.objects.get(forgot_pin_token=token)
            if not user.is_forgot_pin_token_valid():
                return Response({"error": "Token expired or invalid."}, status=400)
            new_pin = str(random.randint(1000, 9999))
            user.set_password(new_pin)  
            user.forgot_pin_token = None
            user.forgot_pin_token_expires = None
            user.save(
                update_fields=["password", "forgot_pin_token", "forgot_pin_token_expires"])
            
            send_new_pin_email(user, new_pin)
            
            return Response({"message": "A new PIN has been sent to your email."})
        except User.DoesNotExist:
            return Response({"error": "Invalid token."}, status=404)
