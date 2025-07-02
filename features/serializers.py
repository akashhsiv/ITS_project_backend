from rest_framework import serializers
from .models import *

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'


#  Filter Items
class ItemFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'sku_code', 'barcode', 'selling_price', 'mrp']

#  Update Settings
class ItemUpdateSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            'category', 'brand', 'tags', 'charges',
            'mrp', 'selling_price', 'includes_tax',
            'allow_price_override', 'allow_discount'
        ]

#  Bulk Image Update
class ItemBulkImageSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    image = serializers.ImageField()

#  Upload Items
class ItemUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

#  Export Items
class ItemExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'sku_code', 'selling_price']

#  Upload Price
class ItemPriceUploadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

#  Bulk Delete
class ItemBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())
    

        
class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'customer', 'status', 'created_at']

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'quantity', 'price']

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'customer', 'status', 'created_at', 'items', 'total', 'discount']

    def get_total(self, obj):
        return obj.total_price()
    
class OrderItemDisplaySerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.item_name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['item_name', 'quantity', 'price']
        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemDisplaySerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'customer', 'status', 'created_at', 'items', 'total', 
                 'discount', 'payment_mode', 'is_paid', 'payment_date']
    
    def get_total(self, obj):
        return obj.total_price()


from rest_framework import serializers

class AddNoteSerializer(serializers.Serializer):
    notes = serializers.CharField(
        allow_blank=True,
        max_length=500,
        help_text="Special note for the order"
    )


from rest_framework import serializers
from decimal import Decimal

class ApplyDiscountSerializer(serializers.Serializer):
    discount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=0,
        help_text="Discount amount to apply"
    )

        
class AddOrderItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(required=False)
    sku_code = serializers.CharField(required=False)
    barcode = serializers.CharField(required=False)
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        if not data.get('item_id') and not data.get('sku_code') and not data.get('barcode'):
            raise serializers.ValidationError("One of item_id, sku_code, or barcode is required.")
        return data



class HoldOrderSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)
    
class DiscardOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)



class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
class RazorpayPaymentVerifySerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

class ManualPaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    mode = serializers.ChoiceField(choices=['cash', 'card', 'upi'])
    amount_received = serializers.DecimalField(max_digits=10, decimal_places=2)
    reference = serializers.CharField(required=False, allow_blank=True)

class UPIPaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    upi_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
class NonChargeablePaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)
    confirm = serializers.BooleanField(help_text="Must be True to confirm non-chargeable payment")

class OrderSummarySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'items', 'total', 'discount']
    
    def get_items(self, obj):
        return [
            {
                'name': item.item.item_name,
                'quantity': item.quantity,
                'price': item.price,
                'subtotal': item.quantity * item.price
            }
            for item in obj.items.all()
        ]
    
    def get_total(self, obj):
        return obj.total_price()

class EditItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class OrderNoteSerializer(serializers.Serializer):
    notes = serializers.CharField()
    
        
class RistaCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = RistaCard
        fields = '__all__'
        
class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'
    
#----------

