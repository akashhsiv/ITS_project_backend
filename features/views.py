from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import filters
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from .models import *
from .serializers import *
import razorpay
from django.conf import settings

import csv
import logging
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


#item management
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer  # default for CRUD
    parser_classes = [MultiPartParser]

    def get_serializer_class(self):
        # Map each custom action to the correct serializer
        if self.action == 'filter_items':
            return ItemFilterSerializer
        if self.action == 'update_item_settings':
            return ItemUpdateSettingsSerializer
        if self.action == 'bulk_image_update':
            return ItemBulkImageSerializer
        if self.action == 'bulk_upload':
            return ItemUploadSerializer
        if self.action == 'export_items':
            return ItemExportSerializer
        if self.action == 'upload_price':
            return ItemPriceUploadSerializer
        if self.action == 'bulk_delete':
            return ItemBulkDeleteSerializer
        return self.serializer_class
    
    #  Filter Items
    @action(detail=True, methods=['get'], url_path='filter', serializer_class=ItemFilterSerializer)
    def filter_items(self, request):
        name = request.query_params.get('name')
        sku = request.query_params.get('sku')
        queryset = self.queryset

        if name:
            queryset = queryset.filter(item_name__icontains=name)
        if sku:
            queryset = queryset.filter(sku_code__icontains=sku)

        serializer = ItemFilterSerializer(queryset, many=True)
        return Response(serializer.data)

    #  Update Item Settings
    @action(detail=True, methods=['patch'], url_path='update-item-settings', serializer_class=ItemUpdateSettingsSerializer)
    def update_item_settings(self, request, pk=None):
        item = self.get_object()
        serializer = ItemUpdateSettingsSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    #  Bulk Image Update
    @action(detail=True, methods=['post'], url_path='bulk-image-update', serializer_class=ItemBulkImageSerializer)
    def bulk_image_update(self, request):
        for key in request.FILES:
            image = request.FILES[key]
            item_id = request.data.get(f"{key}_id")
            if not item_id:
                continue
            try:
                item = Item.objects.get(id=item_id)
                item.image = image
                item.save()
            except Item.DoesNotExist:
                continue
        return Response({'status': 'Images updated'}, status=status.HTTP_200_OK)

    #  Bulk Upload Items
    @action(detail=True, methods=['post'], url_path='bulk-upload', serializer_class=ItemUploadSerializer)
    def bulk_upload(self, request):
        serializer = ItemUploadSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    #  Export Items
    @action(detail=True, methods=['get'], url_path='export', serializer_class=ItemExportSerializer)
    def export_items(self, request):
        items = self.queryset
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="items.csv"'
        writer = csv.writer(response)
        writer.writerow(['id', 'Name', 'SKU', 'Selling Price'])

        for item in items:
            writer.writerow([item.id, item.item_name, item.sku_code, item.selling_price])

        return response

    #  Upload Prices
    @action(detail=True, methods=['post'], url_path='upload-price', serializer_class=ItemPriceUploadSerializer)
    def upload_price(self, request):
        serializer = ItemPriceUploadSerializer(data=request.data.get('items', []), many=True)
        serializer.is_valid(raise_exception=True)

        for data in serializer.validated_data:
            try:
                item = Item.objects.get(id=data['id'])
                item.mrp = data.get('mrp', item.mrp)
                item.selling_price = data.get('selling_price', item.selling_price)
                item.save()
            except Item.DoesNotExist:
                continue

        return Response({'status': 'Prices updated'}, status=status.HTTP_200_OK)

    #  Bulk Delete
    @action(detail=False, methods=['post'], url_path='bulk-delete', serializer_class=ItemBulkDeleteSerializer)
    def bulk_delete(self, request):
        serializer = ItemBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Item.objects.filter(id__in=serializer.validated_data['ids']).delete()
        return Response({'status': 'Deleted successfully'}, status=status.HTTP_200_OK)
    



#  Order interactions (add, discard, hold, close, print)
# class ItemViewSet(viewsets.ModelViewSet):
#     queryset = Item.objects.all()
#     serializer_class = ItemSerializer
#     permission_classes = [AllowAny]  # Adjust permissions as needed

#     @action(detail=False, methods=['get'])
#     def search(self, request):
#         queryset = self.filter_queryset(self.get_queryset())
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)

class OrderInteractionViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_serializer_class(self):
        if self.action == 'add_items':
            return AddOrderItemSerializer
        elif self.action == 'discard':
            return DiscardOrderSerializer
        elif self.action == 'hold':
            return HoldOrderSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'], url_path='filter-by-status')
    def filter_by_status(self, request):
        status_param = request.query_params.get('status')
        if status_param:
            orders = self.get_queryset().filter(status=status_param)
        else:
            orders = self.get_queryset()
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_items(self, request, pk=None):
        """Add items to an order"""
        items_data = request.data.get('items')
        print('RAW BODY:', request.data)
        print('items_data:', items_data)

        # Handle form-encoded single item
        if items_data is None and isinstance(request.data, dict):
            # Check for individual fields
            if any(k in request.data for k in ['item_id', 'sku_code', 'barcode']):
                items_data = [{
                    'item_id': request.data.get('item_id'),
                    'sku_code': request.data.get('sku_code'),
                    'barcode': request.data.get('barcode'),
                    'quantity': request.data.get('quantity', 1)
                }]
            else:
                items_data = []

        serializer = AddOrderItemSerializer(data=items_data, many=True)
        serializer.is_valid(raise_exception=True)

        order = self.get_object()
        added_items = []

        for item_data in serializer.validated_data:
            item = Item.objects.filter(
                id=item_data.get('item_id')
            ).first() or Item.objects.filter(
                sku_code=item_data.get('sku_code')
            ).first() or Item.objects.filter(
                barcode=item_data.get('barcode')
            ).first()

            if item:
                order_item = OrderItem.objects.create(
                    order=order,
                    item=item,
                    quantity=item_data.get('quantity', 1),
                    price=item.selling_price
                )
                added_items.append(order_item)

        output_serializer = OrderItemDisplaySerializer(added_items, many=True)
        return Response({'added_items': output_serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def discard(self, request, pk=None):
        """Discard an order"""
        serializer = DiscardOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = self.get_object()
        order.delete()
        return Response({'message': 'Order discarded'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        """Put an order on hold"""
        serializer = HoldOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = self.get_object()
        order.status = 'held'
        order.save()
        return Response({'message': 'Order placed on hold'})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an order"""
        order = self.get_object()
        order.status = 'closed'
        order.save()
        return Response({'message': 'Order closed successfully'})

    @action(detail=True, methods=['get'])
    def print_receipt(self, request, pk=None):
        """Generate printable receipt"""
        order = self.get_object()
        items = order.items.all()
        
        receipt_data = {
            'order_id': order.id,
            'date': order.created_at.strftime("%Y-%m-%d %H:%M"),
            'customer': order.customer.first_name if order.customer else "Walk-in Customer",
            'items': [{
                'name': item.item.item_name,
                'quantity': item.quantity,
                'price': float(item.price),
                'subtotal': float(item.quantity * item.price)
            } for item in items],
            'total': float(sum(item.quantity * item.price for item in items)),
            'thank_you_message': "THANK YOU! PLEASE VISIT AGAIN!"
        }
        
        return Response({'receipt': receipt_data})


#  Item search by name
class ItemSearchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['item_name']

#Payment Processing

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def get_serializer_class(self):
        if self.action == "summary":
            return OrderSerializer

        if self.action == "initiate_razorpay":
            return PaymentInitiateSerializer
        if self.action == "verify_razorpay":
            return RazorpayPaymentVerifySerializer
        if self.action == "manual_payment":
            return ManualPaymentSerializer
        if self.action == "upi_payment":
            return UPIPaymentSerializer
        # if self.action == "apply_discount":
        #     return ApplyDiscountSerializer 
        if self.action == "edit_item":
            return EditItemSerializer        

        # default: parent implementation
        return super().get_serializer_class()
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get order summary for payment screen"""
        order = self.get_object()
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='edit-item')
    def edit_item(self, request, pk=None):
        """Edit item quantity in order"""
        order = self.get_object()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            order_item = OrderItem.objects.get(order=order, item__id=item_id)
            order_item.quantity = quantity
            order_item.save()
            return Response({'status': 'Item updated'})
        except OrderItem.DoesNotExist:
            return Response({'error': 'Item not found in order'}, status=404)
    
    @action(detail=True, methods=['post'], url_path='add-note')
    def add_note(self, request, pk=None):
        """Add special note to order"""
        order = self.get_object()
        order.special_notes = request.data.get('notes', '')
        order.save()
        return Response({'status': 'Note added'})

    # Razorpay Payment
    @action(detail=False, methods=['post'], url_path='initiate-razorpay')
    def initiate_razorpay(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order_id = serializer.validated_data['order_id']
            order = Order.objects.get(id=order_id, is_paid=False)
            amount = int(order.total_price() * 100)  # Razorpay expects amount in paise
            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture": "1"
            })

            return Response({
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": amount / 100,
                "currency": "INR"
            })
        except Order.DoesNotExist:
            return Response({"error": "Order not found or already paid"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='verify-razorpay')
    def verify_razorpay(self, request):
        serializer = RazorpayPaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })

            order = Order.objects.get(id=data['order_id'])
            order.is_paid = True
            order.payment_mode = 'razorpay'
            order.payment_reference = data['razorpay_payment_id']
            order.payment_date = timezone.now()
            order.amount_paid = order.total_price()
            order.save()
            
            return Response({'message': 'Razorpay payment successful'})
        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    # Manual Payments (Cash/Card)
    @action(detail=False, methods=['post'], url_path='manual-payment')
    def manual_payment(self, request):
        serializer = ManualPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = Order.objects.get(id=serializer.validated_data['order_id'], is_paid=False)
            order.is_paid = True
            order.payment_mode = serializer.validated_data['mode']
            order.payment_reference = serializer.validated_data.get('reference', '')
            order.payment_date = timezone.now()
            order.amount_paid = serializer.validated_data['amount_received']
            order.save()
            
            return Response({'message': f'{serializer.validated_data["mode"].capitalize()} payment successful'})
        except Order.DoesNotExist:
            return Response({"error": "Order not found or already paid"}, status=status.HTTP_404_NOT_FOUND)

    # UPI Payment
    @action(detail=False, methods=['post'], url_path='upi-payment')
    def upi_payment(self, request):
        serializer = UPIPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = Order.objects.get(id=serializer.validated_data['order_id'], is_paid=False)
            
            
            order.is_paid = True
            order.payment_mode = 'upi'
            order.payment_reference = serializer.validated_data['upi_id']
            order.payment_date = timezone.now()
            order.amount_paid = serializer.validated_data['amount']
            order.save()
            
            return Response({'message': 'UPI payment successful'})
        except Order.DoesNotExist:
            return Response({"error": "Order not found or already paid"}, status=status.HTTP_404_NOT_FOUND)

    # Apply Discount
    @action(detail=True, methods=['post'], url_path='apply-discount')
    def apply_discount(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk, is_paid=False)
            discount = Decimal(request.data.get('discount', 0))
            if discount > order.total_price():
                return Response({"error": "Discount cannot be more than total amount"}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            order.discount = discount
            order.save()
            return Response({'message': f'Discount of {discount} applied successfully'})
        except Order.DoesNotExist:
            return Response({"error": "Order not found or already paid"}, status=status.HTTP_404_NOT_FOUND)

# Rista Cards
class RistaCardViewSet(viewsets.ModelViewSet):
    queryset = RistaCard.objects.all()
    serializer_class = RistaCardSerializer

# Appointments
class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    