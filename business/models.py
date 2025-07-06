import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from users.models import Address

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

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Create default branch if this is a new business
        if is_new:
            Branch.objects.create(
                branch_name=f"{self.business_name} - Main Branch",
                branch_code=f"{self.business_name[:3].upper()}MAIN",
                business=self,
                is_default=True,
                status='active'
            )
    
    def __str__(self):
        return self.business_name


class Channel(models.Model):
    """Represents a sales channel for a business"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('closed', 'Closed'),
    ]
    
    branch_name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=50, unique=True)
    business = models.ForeignKey(
        Business, 
        on_delete=models.CASCADE, 
        related_name='branches',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active'
    )
    address = models.OneToOneField(
        Address,
        on_delete=models.PROTECT,
        related_name='branch',
        null=True,
        blank=True
    )
    channels = models.ManyToManyField(
        Channel,
        related_name='branches',
        blank=True
    )
    tax_area = models.CharField(max_length=100, blank=True, null=True)
    pricebook = models.CharField(max_length=100, blank=True, null=True)
    branch_labels = models.CharField(max_length=255, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    is_default = models.BooleanField(default=False, help_text='Indicates if this is the default branch for the business')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_branch_per_business'
            )
        ]

    class Meta:
        verbose_name_plural = 'Branches'
        ordering = ['branch_name']

    def __str__(self):
        return f"{self.branch_name} ({self.branch_code})"