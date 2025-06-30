from django.urls import path
from .views import CustomerListCreateView, CustomerDetailView

urlpatterns = [
    path('customer/', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customer/<str:id>/', CustomerDetailView.as_view(), name='customer-detail'),
]
