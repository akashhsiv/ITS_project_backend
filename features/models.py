from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    
class Menu(models.Model):
    name = models.CharField(max_length=100)

class Brand(models.Model):
    name = models.CharField(max_length=100)

class Tag(models.Model):
    name = models.CharField(max_length=100)

class Charge(models.Model):
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class Item(models.Model):
    item_name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    sku_code = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    supplier_barcodes = models.CharField(max_length=255, blank=True)
    tax_code = models.CharField(max_length=100) # Assuming this is a string representation of the tax code
    nature_of_item = models.CharField(max_length=50, choices=[('Goods', 'Goods'), ('Service', 'Service')])
    display_order = models.PositiveIntegerField(default=0)
    schedules = models.TextField(blank=True)
    images = models.ImageField(upload_to='item_images/', null=True, blank=True)
    service_description = models.TextField(blank=True)
    taxes = models.CharField(max_length=100, choices=[('GST', 'GST'), ('CGST', 'CGST'), ('SGST', 'SGST')], default='None')
    optional_set=models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.TextField(blank=True)
    menus = models.TextField(blank=True) 
    item_brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.TextField(blank=True)
    charges = models.TextField(blank=True)

    measuring_unit = models.CharField(max_length=20, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    includes_tax = models.BooleanField(default=False)
    allow_price_override = models.BooleanField(default=False)
    not_eligible_for_discount = models.BooleanField(default=True)

    def __str__(self):
        return self.item_name
    

class Order(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('held', 'Held'),
        ('closed', 'Closed'),
        ('discarded', 'Discarded')
    ]
    customer = models.ForeignKey("customer.Customer", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='active')  # new: to track order state
    is_paid = models.BooleanField(default=False)
    payment_mode = models.CharField(max_length=20, choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('razorpay', 'Razorpay'),
        ('non_chargeable', 'Non-Chargeable')
    ], null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_non_chargeable = models.BooleanField(default=False)  
    non_chargeable_reason = models.TextField(blank=True, null=True)  # Reason for non-chargeable
    special_notes = models.TextField(blank=True)
    payment_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    change_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def total_price(self):
        return sum(item.price * item.quantity for item in self.items.all()) - self.discount
    
    def calculate_change(self, amount_received):
        total = self.total_price()
        self.payment_received = amount_received
        self.change_due = amount_received - total
        self.save()
        return self.change_due

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    

class RistaCard(models.Model):
    card_number = models.CharField(max_length=100)
    linked_customer = models.ForeignKey("customer.Customer", on_delete=models.CASCADE)

class Appointment(models.Model):
    customer = models.ForeignKey("customer.Customer", on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=50)


