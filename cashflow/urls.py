from django.urls import path
from .views import CashSummaryView

urlpatterns = [
    path('cashsummary/', CashSummaryView.as_view(), name='cash-summary')
]
