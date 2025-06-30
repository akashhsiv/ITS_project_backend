from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Charge(models.Model):
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.amount}"


class Item(models.Model):
    TAX_CHOICES = [("GST", "GST"), ("CGST", "CGST"), ("SGST", "SGST"), ("None", "None")]

    NATURE_CHOICES = [("Goods", "Goods"), ("Service", "Service")]

    item_name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    sku_code = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    supplier_barcodes = models.CharField(max_length=255, blank=True)
    tax_code = models.CharField(max_length=100)
    nature_of_item = models.CharField(max_length=50, choices=NATURE_CHOICES)
    display_order = models.PositiveIntegerField(default=0)
    images = models.ImageField(upload_to="item_images/", null=True, blank=True)
    service_description = models.TextField(blank=True)
    taxes = models.CharField(max_length=100, choices=TAX_CHOICES, default="None")
    optional_set = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    item_brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True
    )
    measuring_unit = models.CharField(max_length=20, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    includes_tax = models.BooleanField(default=False)
    allow_price_override = models.BooleanField(default=False)
    not_eligible_for_discount = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.item_name

    def calculate_tax(self):
        if self.taxes == "GST":
            return self.selling_price * Decimal("0.18")
        elif self.taxes in ["CGST", "SGST"]:
            return self.selling_price * Decimal("0.09")
        return Decimal("0")

    def final_price(self):
        return self.selling_price + self.calculate_tax()


class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("held", "Held"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)
    payment_mode = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.get_status_display()}"

    def total_price(self):
        return sum(item.total_price() for item in self.items.all())

    def total_tax(self):
        return sum(item.tax_amount() for item in self.items.all())

    def final_total(self):
        return self.total_price() + self.total_tax()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.item.item_name} (Order #{self.order.id})"

    def total_price(self):
        return self.price * self.quantity

    def tax_amount(self):
        return self.item.calculate_tax() * self.quantity

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.item.selling_price
        super().save(*args, **kwargs)


class Company(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    address = models.TextField(blank=True)
    tax_info = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class RistaCard(models.Model):
    card_number = models.CharField(max_length=100, unique=True)
    linked_customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Rista Card {self.card_number}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="scheduled"
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Appointment for {self.customer.name} at {self.date_time}"
