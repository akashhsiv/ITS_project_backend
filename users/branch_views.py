from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from django.shortcuts import get_object_or_404
from django.db import transaction

from business.models import Branch
from .models import User, Contact, Address
from .serializers import UserSerializer, UserCreateSerializer
from .email_utils import send_activation_email, send_welcome_email

class BranchUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users within a specific branch.
    URL pattern: /api/<branch_code>/users/
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number']
    ordering_fields = ['first_name', 'last_name', 'date_joined']
    lookup_field = 'id'

    def get_queryset(self):
        branch_code = self.kwargs.get('branch_code')
        return User.objects.filter(branch__branch_code=branch_code, is_active=True)

    def get_branch(self):
        branch_code = self.kwargs.get('branch_code')
        try:
            return Branch.objects.get(branch_code=branch_code, is_active=True)
        except Branch.DoesNotExist:
            raise NotFound("Branch not found or inactive")

    def check_branch_permission(self, branch):
        """Check if the user has permission to access this branch"""
        user = self.request.user
        
        # Superusers can access any branch
        if user.is_superuser:
            return True
            
        # Business admins can access any branch in their business
        if hasattr(user, 'business') and user.business == branch.business:
            return True
            
        # Regular users can only access their own branch
        if hasattr(user, 'branch') and user.branch == branch:
            return True
            
        return False

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return super().get_serializer_class()

    def list(self, request, branch_code=None):
        """List all users in the specified branch"""
        branch = self.get_branch()
        if not self.check_branch_permission(branch):
            raise PermissionDenied("You don't have permission to access this branch")
            
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, branch_code=None):
        """Create a new user in the specified branch"""
        branch = self.get_branch()
        if not self.check_branch_permission(branch):
            raise PermissionDenied("You don't have permission to create users in this branch")
        
        # Regular users can't create admin users
        if not request.user.is_superuser and request.data.get('role') == 'admin':
            raise PermissionDenied("Only superusers can create admin users")
        
        # Set the branch and business for the new user
        request.data['branch_code'] = branch_code
        request.data['business'] = str(branch.business.id) if branch.business else None
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.save()
            
            # Generate a random PIN for the new user
            pin = User.objects.make_random_password(length=4, allowed_chars='0123456789')
            user.set_password(pin)
            user.save()
            
            # Send activation email
            send_activation_email(user, request)
            
            # Send welcome email with PIN
            send_welcome_email(user, pin)
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def retrieve(self, request, id=None, branch_code=None):
        """Retrieve a specific user from the branch"""
        branch = self.get_branch()
        if not self.check_branch_permission(branch):
            raise PermissionDenied("You don't have permission to access this branch")
            
        user = get_object_or_404(User, id=id, branch__branch_code=branch_code)
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    def update(self, request, id=None, branch_code=None):
        """Update a user in the branch"""
        branch = self.get_branch()
        if not self.check_branch_permission(branch):
            raise PermissionDenied("You don't have permission to update users in this branch")
            
        user = get_object_or_404(User, id=id, branch__branch_code=branch_code)
        
        # Prevent changing the branch through this endpoint
        if 'branch_code' in request.data and request.data['branch_code'] != branch_code:
            return Response(
                {"branch_code": "Cannot change branch through this endpoint"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Regular users can't promote users to admin
        if not request.user.is_superuser and 'role' in request.data and request.data['role'] == 'admin':
            return Response(
                {"role": "Only superusers can assign admin role"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Don't update password through this endpoint
        if 'password' in serializer.validated_data:
            del serializer.validated_data['password']
            
        self.perform_update(serializer)
        
        return Response(serializer.data)

    def destroy(self, request, id=None, branch_code=None):
        """Deactivate a user (soft delete)"""
        branch = self.get_branch()
        if not self.check_branch_permission(branch):
            raise PermissionDenied("You don't have permission to deactivate users in this branch")
            
        user = get_object_or_404(User, id=id, branch__branch_code=branch_code)
        
        # Prevent deactivating yourself
        if user == request.user:
            return Response(
                {"detail": "You cannot deactivate your own account"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user.is_active = False
        user.save()
        
        return Response(
            {"detail": "User has been deactivated"},
            status=status.HTTP_200_OK
        )
