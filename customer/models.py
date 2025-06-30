from django.db import models
from django.core.validators import RegexValidator
from users.models import Address  
from cloudinary.models import CloudinaryField


class Company(models.Model):
    name = models.CharField(max_length=255)
    company_id = models.CharField(max_length=64, unique=True)
    tax_id = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Customer(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    id = models.CharField(
        max_length=64,
        primary_key=True,
        validators=[RegexValidator(regex=r'^[a-zA-Z0-9_\-]+$', message='Invalid customer ID')]
    )
    branch_code = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    emails = models.TextField(help_text="Comma-separated list of emails", blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    anniversary_date = models.DateField(blank=True, null=True)

    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    secondary_tax_id = models.CharField(max_length=100, blank=True, null=True)
    tax_state_code = models.CharField(max_length=20, blank=True, null=True)

    addresses = models.ForeignKey(
        Address,
        related_name="customers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    pan_card_front = CloudinaryField(null=True, blank=True)
    pan_card_back = CloudinaryField(null=True, blank=True)

    is_blocked = models.BooleanField(default=False)
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}"


class Membership(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='membership')
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()


class LoyaltyInfo(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='loyalty_info')
    points = models.DecimalField(max_digits=10, decimal_places=2)
    reserved_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    points_ending_this_month = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    points_ending_next_month = models.DecimalField(max_digits=10, decimal_places=2, default=0)
