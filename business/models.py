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

    # Basic Details
    business_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=255, blank=True)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPES)

    # Location Fields
    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Primary Contact Fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True)
    mobile = models.CharField(max_length=20)
    email = models.EmailField(unique=True)

    
    # Activation email fields
    account_number = models.CharField(max_length=20, blank=True, null=True)
    device_key = models.CharField(max_length=20, blank=True, null=True)
    device_label = models.CharField(max_length=100)
    pin = models.CharField(max_length=6, blank=True, null=True)
    user_id = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    device_key_expires = models.DateTimeField(null=True, blank=True)
    activation_token = models.UUIDField(default=uuid.uuid4, editable=True, null=True, blank=True)
    activation_token_expires = models.DateTimeField(blank=True, null=True)

    # Forgot PIN
    forgot_pin_token = models.UUIDField(null=True, blank=True)
    forgot_pin_token_expires = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.business_name
        
    def generate_activation_token(self):
        self.activation_token = uuid.uuid4()
        self.activation_token_expires = timezone.now() + timedelta(hours=24)  # Token expires in 24 hours
        self.save(update_fields=['activation_token', 'activation_token_expires'])
        return self.activation_token
        
    def activate_account(self):
        self.is_active = True
        self.activation_token = None
        self.activation_token_expires = None
        self.save(update_fields=['is_active', 'activation_token', 'activation_token_expires'])
        
    def is_activation_token_valid(self):
        if not self.activation_token or not self.activation_token_expires:
            return False
        return timezone.now() < self.activation_token_expires
    
    def generate_forgot_pin_token(self):
        self.forgot_pin_token = uuid.uuid4()
        self.forgot_pin_token_expires = timezone.now() + timedelta(hours=24)
        self.save(update_fields=['forgot_pin_token', 'forgot_pin_token_expires'])
        return self.forgot_pin_token
    
    def is_forgot_pin_token_valid(self):
        return self.forgot_pin_token and self.forgot_pin_token_expires and timezone.now() < self.forgot_pin_token_expires


