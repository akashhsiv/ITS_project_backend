from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.db.models import Sum, F

from cashflow.models import Payment, ReturnOrder, Tip
from features.models import Order, OrderItem

class CashSummaryView(APIView):
    def get(self, request):
        branch = request.query_params.get('branch')
        period = request.query_params.get('period')

        if not branch or not period:
            return Response({'error': 'branch and period are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if len(period) == 10:  # daily
                start_date = make_aware(datetime.strptime(period, '%Y-%m-%d'))
                end_date = start_date.replace(hour=23, minute=59, second=59)
            elif len(period) == 7:  # monthly
                start_date = make_aware(datetime.strptime(period, '%Y-%m'))
                end_date = make_aware(datetime(start_date.year, start_date.month + 1, 1)) if start_date.month < 12 else make_aware(datetime(start_date.year + 1, 1, 1))
            else:
                raise ValueError
        except ValueError:
            return Response({'error': 'Invalid period format'}, status=status.HTTP_400_BAD_REQUEST)

        # 🧠 Fetch all orders in range (filter by branch if model has it)
        orders = Order.objects.filter(created_at__range=(start_date, end_date))
        order_items = OrderItem.objects.filter(order__in=orders)

        # 🧮 Start calculating
        gross = order_items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        discount = orders.aggregate(total=Sum('discount'))['total'] or 0
        tips = Tip.objects.filter(order__in=orders)
        tip_total = tips.aggregate(total=Sum('amount'))['total'] or 0

        payments = Payment.objects.filter(order__in=orders)
        payment_total = payments.aggregate(total=Sum('amount'))['total'] or 0

        # Assume round_off, cost, tax handled in fields (customize if needed)
        round_off = orders.aggregate(total=Sum('change_due'))['total'] or 0
        returns = ReturnOrder.objects.filter(original_order__in=orders)
        return_total = returns.count()  # or custom amount

        items = []
        for item in order_items.values('item__sku_code', 'item__item_name', 'item__item_brand__name', 'item__category__name', 'item__measuring_unit').annotate(
            total_qty=Sum('quantity'),
            gross_amount=Sum(F('price') * F('quantity')),
        ):
            items.append({
                "skuCode": item['item__sku_code'],
                "itemName": item['item__item_name'],
                "brandName": item['item__item_brand__name'],
                "accountName": "",  # if using account
                "categoryName": item['item__category__name'],
                "subCategory": "",  # if you have subcategory
                "itemNature": "Goods",  # or from item
                "type": "Main",  # default
                "measuringUnit": item['item__measuring_unit'],
                "itemTotalDiscountAmount": 0,
                "itemTotalNetAmount": 0,
                "itemTotalQty": item['total_qty'],
                "itemTotalgrossAmount": item['gross_amount'],
                "itemTotaltaxAmount": 0,
            })

        return Response({
            "grossAmount": gross,
            "returnAmount": return_total,
            "discountTotal": discount,
            "directChargeTotal": 0,
            "netAmount": gross - discount,
            "chargeTotal": 0,
            "taxTotal": 0,
            "roundOffTotal": round_off,
            "tipTotal": tip_total,
            "revenue": gross + tip_total,
            "paymentTotal": payment_total,
            "balanceAmount": (gross - discount) - payment_total,
            "costOfGoodsSold": 0,
            "marginOnNetSales": 0,
            "discounts": [],
            "categories": [],
            "charges": [],
            "taxes": [],
            "tips": [{"user": t.user.username if t.user else "Anonymous", "amount": t.amount} for t in tips],
            "payments": [{"mode": p.mode, "amount": p.amount} for p in payments],
            "noOfSales": orders.count(),
            "avgSaleAmount": gross / orders.count() if orders.count() else 0,
            # "noOfPeople": sum([o.number_of_people for o in orders if hasattr(o, 'number_of_people')]),  # Removed due to missing attribute
            # "avgSaleAmountPerPerson": (gross / sum([o.number_of_people for o in orders if hasattr(o, 'number_of_people')])) if orders else 0,  # Removed due to missing attribute
            "noOfPeople": 0,
            "avgSaleAmountPerPerson": 0,
            "asOfTime": datetime.now().isoformat(),
            "sessionSummary": [],
            "channelSummary": [],
            "costs": [],
            "items": items,
            "accounts": [],
            "accountsWiseChannels": []
        })
