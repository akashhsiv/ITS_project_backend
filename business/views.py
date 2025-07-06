import logging
import random
import string

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, renderers, permissions
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, BasePermission
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Business, Branch, Channel
from django.db import transaction
from .email_utils import send_welcome_email
from .serializers import (
    BusinessReadSerializer,
    BusinessCreateUpdateSerializer,
    BranchSerializer,
    ChannelSerializer,
)
from users.models import User
from users.permissions import IsAdminUser, IsFirstUserOrAdmin
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def generate_key(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()

    def get_permissions(self):
        """
        Allow unauthenticated access for business creation when no users exist,
        otherwise require authentication for create action.
        Always allow list action without authentication.
        """
        if self.action == 'list':
            return [AllowAny()]
            
        if self.action == 'create':
            # Allow creation without authentication if no users exist yet
            if not User.objects.exists():
                return [AllowAny()]
            return [IsAuthenticated()]
            
        # For all other actions, require authentication
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return BusinessReadSerializer
        return BusinessCreateUpdateSerializer
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        
        # Get the created user to include in the response
        user = business.users.order_by('created_at').first()
        
        return Response(
            {
                "message": "Business created successfully. Please check your email to activate your account.",
                "email": user.contact.email if user and hasattr(user, 'contact') and user.contact else "No email provided"
            },
            status=status.HTTP_201_CREATED
        )


class IsAdminRole(BasePermission):
    """
    Allows access only to users with role='admin'.
    """
    def has_permission(self, request, view):
        print("\n=== DEBUG: IsAdminRole Check ===")
        print(f"User: {request.user}")
        print(f"User authenticated: {request.user.is_authenticated}")
        
        if not request.user or not request.user.is_authenticated:
            print("FAIL: No user or not authenticated")
            return False
            
        has_role = hasattr(request.user, 'role')
        print(f"User has 'role' attribute: {has_role}")
        
        if has_role:
            print(f"User role: '{request.user.role}'")
            is_admin = request.user.role == 'admin'
            print(f"Is admin: {is_admin}")
        else:
            print("User does not have 'role' attribute")
            is_admin = False
            
        print(f"=== END DEBUG ===\n")
        return is_admin


class BranchViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing branches.
    """
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    lookup_field = 'branch_code'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsAdminRole]
        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """
        Pass request context to serializer.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """
        Create a new branch, tied to the user's business.
        """
        try:
            data = request.data.copy()
            logger.info(f"[BRANCH CREATE] Incoming data: {data}")

            if 'business' not in data and hasattr(request.user, 'business'):
                data['business'] = request.user.business.id
                logger.info(f"[BRANCH CREATE] Assigned user's business: {data['business']}")

            if 'address' not in data:
                return Response(
                    {"address": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            logger.info("[BRANCH CREATE] Serializer valid")

            self.perform_create(serializer)
            logger.info(f"[BRANCH CREATE] Branch created: {serializer.data}")

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )

        except Exception as e:
            logger.error(f"[BRANCH CREATE] Exception: {str(e)}", exc_info=True)
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        """
        Internal create logic for setting defaults and validation.
        """
        request_user = self.request.user
        data = self.request.data
        logger.info(f"[BRANCH SAVE] perform_create with data: {data}")

        business = serializer.validated_data.get('business') or getattr(request_user, 'business', None)
        if not business:
            raise ValidationError("Business is required and could not be determined.")

        if not request_user.is_superuser and business != request_user.business:
            raise PermissionDenied("You don't have permission to add branches to this business.")

        branch_name = serializer.validated_data.get('branch_name')
        if Branch.objects.filter(business=business, branch_name=branch_name).exists():
            raise ValidationError({"branch_name": ["Branch name already exists for this business."]})

        is_first_branch = not Branch.objects.filter(business=business).exists()
        branch = serializer.save(business=business, is_default=is_first_branch)

        if not branch.branch_code:
            branch.branch_code = f"{business.business_name[:3].upper()}{branch.id:04d}"
            branch.save()
            logger.info(f"[BRANCH SAVE] Generated branch code: {branch.branch_code}")
class ChannelViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing sales channels.
    Only accessible by admin users.
    """
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'name'
    lookup_value_regex = '[^/]+'  # Allow any character except '/' in the URL


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
            send_welcome_email(user, business, pin)
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
