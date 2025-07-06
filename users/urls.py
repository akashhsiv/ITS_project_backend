from django.urls import path, include
from .views import UserActivationView, LoginView, UserViewSet, ForgotPinConfirmView
from .branch_views import BranchUserViewSet
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

# Branch-specific user endpoints
branch_user_view = BranchUserViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
branch_user_detail_view = BranchUserViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # Original user endpoints
    path('', include(router.urls)),
    
    # Authentication endpoints
    path("api/auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair_alt"),
    
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh_alt"),
    
    path("api/auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
    path("auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist_alt"),
    
    # Handle all possible activation URL patterns
    path('api/users/activate/<uuid:token>/', UserActivationView.as_view(), name='user-activate'),
    path('users/activate/<uuid:token>/', UserActivationView.as_view(), name='user-activate-alt'),
    # Handle the case where frontend adds an extra /api/ prefix
    path('api/api/users/activate/<uuid:token>/', UserActivationView.as_view(), name='user-activate-legacy'),
    
    path('api/forgot_pin/confirm/<uuid:token>/', ForgotPinConfirmView.as_view(), name='forgot-pin-confirm'),
    path('forgot_pin/confirm/<uuid:token>/', ForgotPinConfirmView.as_view(), name='forgot-pin-confirm-alt'),
    
    # Branch-specific user management
    path('<str:branch_code>/users/', branch_user_view, name='branch-user-list'),
    path('<str:branch_code>/users/<str:id>/', branch_user_detail_view, name='branch-user-detail'),
]
