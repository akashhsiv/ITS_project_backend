from rest_framework import serializers
from .models import *
from django.db import transaction
import base64
from django.core.files.base import ContentFile

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class ChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charge
        fields = '__all__'

class ItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False
    )
    item_brand = BrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source='item_brand',
        write_only=True,
        required=False
    )
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_image_url(self, obj):
        if obj.images:
            return self.context['request'].build_absolute_uri(obj.images.url)
        return None

class ItemFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'sku_code', 'barcode', 'selling_price', 'mrp']

class ItemUpdateSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            'category', 'item_brand', 'taxes',
            'mrp', 'selling_price', 'includes_tax',
            'allow_price_override', 'not_eligible_for_discount'
        ]

class ItemBulkImageSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    image = serializers.ImageField()

class ItemUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

class ItemExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'item_name', 'sku_code', 'selling_price']

class ItemPriceUploadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

class ItemBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(),
        source='item',
        write_only=True
    )
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ('price', 'total')
    
    def get_total(self, obj):
        return obj.total_price()

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        source='customer',
        write_only=True,
        required=False
    )
    subtotal = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = '__all__'
    
    def get_subtotal(self, obj):
        return obj.total_price()
    
    def get_tax(self, obj):
        return obj.total_tax()
    
    def get_total(self, obj):
        return obj.final_total()

class AddOrderItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(required=False)
    sku_code = serializers.CharField(required=False)
    barcode = serializers.CharField(required=False)
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        if not any([data.get('item_id'), data.get('sku_code'), data.get('barcode')]):
            raise serializers.ValidationError("At least one identifier (item_id, sku_code, or barcode) is required.")
        return data

class HoldOrderSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)

class DiscardOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

class PaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    method = serializers.ChoiceField(choices=[
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('mobile', 'Mobile Payment'),
        ('rista_card', 'Rista Card')
    ])
    card_details = serializers.JSONField(required=False)
    rista_card_number = serializers.CharField(required=False)
    
    def validate(self, data):
        method = data['method']
        if method == 'card' and not data.get('card_details'):
            raise serializers.ValidationError("Card details are required for card payments")
        if method == 'rista_card' and not data.get('rista_card_number'):
            raise serializers.ValidationError("Rista card number is required")
        return data

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class RistaCardSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    
    class Meta:
        model = RistaCard
        fields = '__all__'

class AppointmentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    
    class Meta:
        model = Appointment
        fields = '__all__'