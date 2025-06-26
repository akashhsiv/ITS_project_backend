import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Business(models.Model):
    BUSINESS_TYPES = [
        ('retail', 'Retail'),
        ('electronics', 'Electronics'),
        ('fashion', 'Fashion'),
        ('food', 'Food'),
        ('health', 'Health'),
        ('home', 'Home'),
        ('office', 'Office'),
        ('restaurant', 'Restaurant'),
        ('services', 'Services'),
    ]

    account_number = models.CharField(max_length=20, blank=True, null=True)
    business_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=255, blank=True)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPES)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.business_name

    