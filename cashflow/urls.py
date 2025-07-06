from django.urls import path
from rest_framework.permissions import IsAuthenticated
from .views import CashSummaryView

urlpatterns = [
    path('ordermanagement/dailysales/', 
         CashSummaryView.as_view(permission_classes=[IsAuthenticated]), 
         name='daily-sales'
    ),
    # Keeping old endpoints for backward compatibility
    path('sales/report/', CashSummaryView.as_view(), name='sales-report'),
    path('cashsummary/', CashSummaryView.as_view(), name='cash-summary')
]
