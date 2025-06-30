from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, CustomerListCreateView, CustomerDetailView,CouponCampaignViewSet


router = DefaultRouter()
router.register(r'coupon-campaigns', CouponCampaignViewSet)
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('customer/', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customer/<str:id>/', CustomerDetailView.as_view(), name='customer-detail'),
]


urlpatterns += [
    path('', include(router.urls))
]