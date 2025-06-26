from django.urls import path
from .views import PINLoginView, UserCreateAPIView, UserActivationView

urlpatterns = [
    path('api/users/login/', PINLoginView.as_view(), name='pin-login'),
    path('api/users/create/', UserCreateAPIView.as_view(), name='user-create'),
    path('api/users/activate/<uuid:token>/', UserActivationView.as_view(), name='user-activate'),
]
