from django.db import models

from users.models import User


class Payment(models.Model):
    order = models.ForeignKey("features.Order", on_delete=models.CASCADE, related_name="payments")
    mode = models.CharField(max_length=20, choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('razorpay', 'Razorpay'),
        ('non_chargeable', 'Non-Chargeable'),
    ])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    received_at = models.DateTimeField(auto_now_add=True)

class Tip(models.Model):
    order = models.ForeignKey("features.Order", on_delete=models.CASCADE, related_name="tips")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class Session(models.Model):
    name = models.CharField(max_length=100)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

class ReturnOrder(models.Model):
    original_order = models.ForeignKey("features.Order", on_delete=models.CASCADE, related_name="returns")
    return_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
