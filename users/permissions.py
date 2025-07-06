from rest_framework import permissions
from users.models import User

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow users with Admin role to access the view.
    """
    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Check if the user has the Admin role
        return request.user.role == 'admin'


class IsFirstUserOrAdmin(permissions.BasePermission):
    """
    Allow access if no users exist yet (first user) or if user is admin.
    """
    def has_permission(self, request, view):
        # Allow if no users exist yet
        if not User.objects.exists():
            return True
            
        # For existing users, require admin authentication
        if not request.user or not request.user.is_authenticated:
            return False
            
        return request.user.role == 'admin'