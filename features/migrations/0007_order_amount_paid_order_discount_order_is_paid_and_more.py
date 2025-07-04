# Generated by Django 5.2.3 on 2025-06-30 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0006_company_customer_appointment_order_orderitem_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='amount_paid',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='is_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_mode',
            field=models.CharField(blank=True, choices=[('cash', 'Cash'), ('card', 'Card'), ('upi', 'UPI'), ('razorpay', 'Razorpay')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_reference',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
