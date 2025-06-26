from django.urls import path, include
from .views import  UserActivationView, LoginView, UserViewSet, ForgotPinConfirmView
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path("api/auth/login/",   LoginView.as_view(),         name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(),  name="token_refresh"),
    path("api/auth/logout/",  TokenBlacklistView.as_view(), name="token_blacklist"),
    path('api/users/activate/<uuid:token>/', UserActivationView.as_view(), name='user-activate'),
    path('forgot_pin/confirm/<uuid:token>/', ForgotPinConfirmView.as_view(), name='forgot-pin-confirm'),

]
