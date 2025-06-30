from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework import filters
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import *
from .serializers import *
import razorpay
from django.conf import settings
import csv
import logging


logger = logging.getLogger(__name__)

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.filter(is_active=True)
    serializer_class = ItemSerializer
    parser_classes = [MultiPartParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['item_name', 'sku_code', 'barcode']
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ItemFilterSerializer
        elif self.action == 'update_settings':
            return ItemUpdateSettingsSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'])
    def filter(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ItemFilterSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='update-settings')
    def update_settings(self, request, pk=None):
        item = self.get_object()
        serializer = ItemUpdateSettingsSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='bulk-image-update')
    def bulk_image_update(self, request):
        serializer = ItemBulkImageSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            for item_data in serializer.validated_data:
                item = Item.objects.get(id=item_data['item_id'])
                item.images = item_data['image']
                item.save()
        
        return Response({'status': 'Images updated successfully'})

    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        serializer = ItemUploadSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='export')
    def export_items(self, request):
        items = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="items_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'SKU', 'Selling Price'])
        
        for item in items:
            writer.writerow([item.id, item.item_name, item.sku_code, item.selling_price])
        
        return response

    @action(detail=False, methods=['post'], url_path='upload-price')
    def upload_price(self, request):
        serializer = ItemPriceUploadSerializer(data=request.data.get('items', []), many=True)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            for price_data in serializer.validated_data:
                item = Item.objects.get(id=price_data['id'])
                if 'mrp' in price_data:
                    item.mrp = price_data['mrp']
                if 'selling_price' in price_data:
                    item.selling_price = price_data['selling_price']
                item.save()
        
        return Response({'status': 'Prices updated successfully'})

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        serializer = ItemBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        Item.objects.filter(id__in=serializer.validated_data['ids']).update(is_active=False)
        return Response({'status': 'Items deleted successfully'})

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return OrderSerializer
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
    @action(detail=True, methods=['post'], url_path='add-items')
    def add_items(self, request, pk=None):
        order = self.get_object()
        serializer = AddOrderItemSerializer(data=request.data.get('items', []), many=True)
        serializer.is_valid(raise_exception=True)
        
        added_items = []
        with transaction.atomic():
            for item_data in serializer.validated_data:
                item = None
                if item_data.get('item_id'):
                    item = get_object_or_404(Item, id=item_data['item_id'])
                elif item_data.get('sku_code'):
                    item = get_object_or_404(Item, sku_code=item_data['sku_code'])
                elif item_data.get('barcode'):
                    item = get_object_or_404(Item, barcode=item_data['barcode'])
                
                if item:
                    order_item, created = OrderItem.objects.get_or_create(
                        order=order,
                        item=item,
                        defaults={
                            'quantity': item_data['quantity'],
                            'price': item.selling_price
                        }
                    )
                    if not created:
                        order_item.quantity += item_data['quantity']
                        order_item.save()
                    added_items.append(order_item)
        
        return Response(OrderItemSerializer(added_items, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        order = self.get_object()
        serializer = HoldOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order.status = 'held'
        order.save()
        return Response({'status': 'Order held successfully'})

    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        order = self.get_object()
        serializer = DiscardOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order.status = 'cancelled'
        order.save()
        return Response({'status': 'Order discarded successfully'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        order.status = 'completed'
        order.save()
        return Response({'status': 'Order completed successfully'})

    @action(detail=True, methods=['get'])
    def print(self, request, pk=None):
        order = self.get_object()
        items = order.items.all()
        
        receipt_data = {
            'order_id': order.id,
            'customer': order.customer.name if order.customer else 'Walk-in Customer',
            'date': order.created_at.strftime("%Y-%m-%d %H:%M"),
            'items': [],
            'subtotal': float(order.total_price()),
            'tax': float(order.total_tax()),
            'total': float(order.final_total()),
        }
        
        for item in items:
            receipt_data['items'].append({
                'name': item.item.item_name,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.total_price())
            })
        
        return Response(receipt_data)

class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate(self, request):
        order_id = request.data.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        
        try:
            razorpay_order = razorpay_client.order.create({
                'amount': int(order.final_total() * 100),
                'currency': 'INR',
                'payment_capture': 1
            })
            
            return Response({
                'razorpay_order_id': razorpay_order['id'],
                'amount': order.final_total(),
                'currency': 'INR',
                'key': settings.RAZORPAY_KEY_ID
            })
        except Exception as e:
            logger.error(f"Payment initiation failed: {str(e)}")
            return Response(
                {'error': 'Payment initiation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='verify')
    def verify(self, request):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })
            
            order = Order.objects.get(id=data['order_id'])
            order.is_paid = True
            order.payment_mode = 'razorpay'
            order.status = 'completed'
            order.save()
            
            return Response({'status': 'Payment verified and completed'})
        
        except razorpay.errors.SignatureVerificationError:
            return Response(
                {'error': 'Payment verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return Response(
                {'error': 'Payment processing failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='manual')
    def manual(self, request):
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            order = Order.objects.get(id=data['order_id'])
            order.is_paid = True
            order.payment_mode = data['method']
            order.status = 'completed'
            order.save()
            
            return Response({'status': f'Manual payment recorded ({data["method"]})'})
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'email', 'phone']

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

class RistaCardViewSet(viewsets.ModelViewSet):
    queryset = RistaCard.objects.filter(is_active=True)
    serializer_class = RistaCardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['card_number', 'linked_customer__name']

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['customer__name', 'status']