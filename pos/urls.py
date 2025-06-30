from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ItemViewSet,
    OrderViewSet,
    PaymentViewSet,
    CustomerViewSet,
    CompanyViewSet,
    RistaCardViewSet,
    AppointmentViewSet
)

router = DefaultRouter()
router.register(r'items', ItemViewSet, basename='items')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'customers', CustomerViewSet, basename='customers')
router.register(r'companies', CompanyViewSet, basename='companies')
router.register(r'rista-cards', RistaCardViewSet, basename='rista-cards')
router.register(r'appointments', AppointmentViewSet, basename='appointments')

payment_urls = [
    path('initiate/', PaymentViewSet.as_view({'post': 'initiate'}), name='payment-initiate'),
    path('verify/', PaymentViewSet.as_view({'post': 'verify'}), name='payment-verify'),
    path('manual/', PaymentViewSet.as_view({'post': 'manual'}), name='payment-manual'),
]

urlpatterns = [
    path('order/', include(router.urls)),
    path('payments/', include(payment_urls)),
]