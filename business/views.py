
import logging
import random
import string

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Business
from datetime import timedelta
from django.utils import timezone
from django.db            import transaction

from .email_utils import send_welcome_email
from .serializers import (
    BusinessReadSerializer,
    BusinessCreateUpdateSerializer,
)

from users.models         import User
from business.models      import Business

logger = logging.getLogger(__name__)


def generate_key(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return BusinessReadSerializer
        return BusinessCreateUpdateSerializer
#     
class BusinessActivationView(APIView):
    """
    Activate a user account given its activation token.
    URL pattern example:  /activate/<uuid:token>/
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        user = get_object_or_404(
            User,
            activation_token=token,
            is_active=False,
        )

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
            business: Business | None = user.business
            if business and not business.is_active:
                business.is_active = True
                business.save(update_fields=["is_active"])

        try:
            send_welcome_email(user, business , pin)
        except Exception:
            logger.exception("Failed to send welcome e-mail after activation")

        return Response(
            {
                "success": True,
                "message": "Your account has been activated. "
                           "Please check your inbox for your credentials.",
            },
            status=status.HTTP_200_OK,
        )