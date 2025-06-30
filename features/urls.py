from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, OrderInteractionViewSet, ItemSearchViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'orders/interaction', OrderInteractionViewSet, basename='order-interaction')
router.register(r'items/search', ItemSearchViewSet, basename='item-search')
router.register(r'payment', PaymentViewSet, basename='payments')

urlpatterns = [path('POS/', include(router.urls))]
