from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BusinessViewSet, 
    BusinessActivationView,
    BranchViewSet,
    ChannelViewSet
)

router = DefaultRouter()
router.register(r'businesses', BusinessViewSet)
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'channels', ChannelViewSet, basename='channel')

urlpatterns = [
    path('', include(router.urls)),
    path('activate/<uuid:token>/', BusinessActivationView.as_view(), name='business-activate'),
]
