from django.contrib.auth.models import BaseUserManager
from datetime import timedelta
import random
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class Address(models.Model):
    address_line1 = models.TextField()
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)


    def __str__(self):
        return f"{self.address_line1}, {self.city or ''}"


class Contact(models.Model):
    class TitleChoices(models.TextChoices):
        MR = "Mr", "Mr."
        MRS = "Mrs", "Mrs."
        MS = "Ms", "Ms."
        DR = "Dr", "Dr."
        PROF = "Prof", "Prof."
        MX = "Mx", "Mx."
        NONE = "", "—"

    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(
        max_length=10, choices=TitleChoices.choices, blank=True, null=True
    )

    def __str__(self):
        return f"{self.title or ''} {self.phone or self.email or 'No Contact Info'}".strip()


class Role(models.TextChoices):
    ADMIN = "Admin", "ADMIN"
    MANAGER = "Manager", "MANAGER"
    CASHIER = "Cashier", "CASHIER"


class TitleChoices(models.TextChoices):
    MR = "Mr", "Mr."
    MRS = "Mrs", "Mrs."
    MISS = "Miss", "Miss"
    MS = "Ms", "Ms."
    DR = "Dr", "Dr."
    PROF = "Prof", "Prof."
    MX = "Mx", "Mx."


class UserManager(BaseUserManager):
    def create_user(self, user_id, pin=None, **extra_fields):
        if not user_id:
            raise ValueError("User must have a user_id")
        user = self.model(user_id=user_id, **extra_fields)
        user.set_password(pin)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(user_id, password, **extra_fields)

    def get_by_natural_key(self, user_id):
        return self.get(user_id=user_id)


class User(AbstractBaseUser):
    objects = UserManager()

    # Unique User ID (generated)
    user_id = models.CharField(max_length=20, unique=True)

    # Business reference
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # Optional FK to extended contact/address tables
    contact = models.OneToOneField(
        "Contact", on_delete=models.SET_NULL, null=True, blank=True
    )
    address = models.ForeignKey(
        "Address", on_delete=models.SET_NULL, null=True, blank=True
    )

    # Activation fields
    is_active = models.BooleanField(default=False)
    activation_token = models.UUIDField(
        default=uuid.uuid4, editable=False, null=True, blank=True
    )
    activation_token_expires = models.DateTimeField(blank=True, null=True)

    # Roles & Access
    role = models.CharField(max_length=50,  choices=Role.choices, default=Role.CASHIER)

    permitted_stores = ArrayField(
        base_field=models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="List of permitted stores (any string value)",
    )
    permitted_licenses = ArrayField(
        base_field=models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="List of permitted licenses (any string value)",
    )
    permitted_brands = ArrayField(
        base_field=models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="List of permitted brands (any string value)",
    )

    access_profile = models.TextField(blank=True, null=True)
    access_expires_at = models.DateTimeField(blank=True, null=True)

    can_backdate_orders = models.BooleanField(default=False)
    can_login_offline = models.BooleanField(default=False)
    allowed_actions = ArrayField(
        models.CharField(max_length=50), blank=True, default=list
    )
    all_actions_enabled = models.BooleanField(default=False)

    # Device and login linkage
    account_number = models.CharField(max_length=20, blank=True, null=True)
    device_key = models.CharField(max_length=20, blank=True, null=True)
    device_label = models.CharField(max_length=100, blank=True)

    # Field for Go Offline functionality
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='offline')
    # Activation flow
    is_active = models.BooleanField(default=False)
    activation_token = models.UUIDField(
        default=uuid.uuid4, editable=True, null=True, blank=True
    )
    activation_token_expires = models.DateTimeField(blank=True, null=True)

    # Forgot PIN flow
    forgot_pin_token = models.UUIDField(null=True, blank=True)
    forgot_pin_token_expires = models.DateTimeField(null=True, blank=True)

    # Meta
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    def __str__(self):
        return f"{self.user_id} - {self.first_name} {self.last_name}"

    def is_action_allowed(self, action: str) -> bool:
        if not self.is_active:
            return False
        if self.access_expires_at and timezone.now() > self.access_expires_at:
            return False
        if self.all_actions_enabled:
            return True
        return action in self.allowed_actions

    def generate_activation_token(self):
        self.activation_token = uuid.uuid4()
        self.activation_token_expires = timezone.now() + timedelta(
            hours=24
        )  # Token expires in 24 hours
        self.save(update_fields=["activation_token",
                  "activation_token_expires"])
        return self.activation_token

    def activate_account(self):
        self.is_active = True
        self.activation_token = None
        self.activation_token_expires = None
        pin = str(random.randint(1000, 9999))
        self.set_password(pin)
        self.save(
            update_fields=["is_active", "activation_token",
                           "activation_token_expires", "password"]
        )
        return pin

    def is_activation_token_valid(self):
        if not self.activation_token or not self.activation_token_expires:
            return False
        return timezone.now() < self.activation_token_expires

    def generate_forgot_pin_token(self):
        self.forgot_pin_token = uuid.uuid4()
        self.forgot_pin_token_expires = timezone.now() + timedelta(hours=24)
        self.save(update_fields=["forgot_pin_token",
                  "forgot_pin_token_expires"])
        return self.forgot_pin_token

    def is_forgot_pin_token_valid(self):
        return (
            self.forgot_pin_token
            and self.forgot_pin_token_expires
            and timezone.now() < self.forgot_pin_token_expires
        )
