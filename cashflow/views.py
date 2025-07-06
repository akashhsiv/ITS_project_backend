from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, Q, F
from features.models import Order, OrderItem
from cashflow.models import Payment, Tip, Session, ReturnOrder
from users.models import User
from customer.models import Customer
from django.db.models.functions import TruncDate, TruncMonth

class CashSummaryView(APIView):
    def get(self, request):
        # Get branch from authenticated user
        if not hasattr(request.user, 'branch'):
            return Response(
                {'error': 'User is not associated with any branch'}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        branch = request.user.branch
        print("🔍 Branch:", branch)
        period = request.query_params.get('period')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        print("📅 Start Date:", start_date_str)
        print("📅 End Date:", end_date_str)

        try:
            # Handle date range
            if start_date_str and end_date_str:
                start_date = make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                end_date = make_aware(datetime.strptime(end_date_str, '%Y-%m-%d')).replace(hour=23, minute=59, second=59)
            elif period:
                if period == 'today':
                    start_date = make_aware(datetime.now().replace(hour=0, minute=0, second=0))
                    end_date = make_aware(datetime.now().replace(hour=23, minute=59, second=59))
                elif period == 'yesterday':
                    yesterday = datetime.now() - timedelta(days=1)
                    start_date = make_aware(yesterday.replace(hour=0, minute=0, second=0))
                    end_date = make_aware(yesterday.replace(hour=23, minute=59, second=59))
                elif period == 'this_month':
                    today = datetime.now()
                    start_date = make_aware(datetime(today.year, today.month, 1))
                    next_month = today.month % 12 + 1
                    next_year = today.year + (1 if next_month == 1 else 0)
                    end_date = make_aware(datetime(next_year, next_month, 1) - timedelta(days=1))
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                elif period == 'last_month':
                    today = datetime.now()
                    first_day_this_month = today.replace(day=1)
                    last_day_last_month = first_day_this_month - timedelta(days=1)
                    start_date = make_aware(datetime(last_day_last_month.year, last_day_last_month.month, 1))
                    end_date = make_aware(last_day_last_month.replace(hour=23, minute=59, second=59))
                else:
                    valid_periods = ['today', 'yesterday', 'this_month', 'last_month']
                    return Response(
                        {'error': f'Invalid period. Valid options are: {", ".join(valid_periods)}'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Default to today if no date range or period specified
                start_date = make_aware(datetime.now().replace(hour=0, minute=0, second=0))
                end_date = make_aware(datetime.now().replace(hour=23, minute=59, second=59))

            # Get orders for the current branch in the date range
            # First get all customers in the current branch
            customers_in_branch = Customer.objects.filter(branch=request.user.branch)
            print("👥 Customers in Branch:", customers_in_branch.count())

            # Then get orders for those customers
            orders = Order.objects.filter(
                created_at__range=(start_date, end_date),
                customer__in=customers_in_branch
            )
            print("📦 Orders found:", orders.count())

            # Get related data
            order_items = OrderItem.objects.filter(order__in=orders)
            payments = Payment.objects.filter(order__in=orders)
            print("🧾 Order Items:", order_items.count())
            print("💰 Payments found:", payments.count())
            tips = Tip.objects.filter(order__in=orders)
            returns = ReturnOrder.objects.filter(original_order__in=orders)
            sessions = Session.objects.filter(
                started_at__lte=end_date,
                ended_at__gte=start_date
            )

            # Calculate metrics
            gross = order_items.aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
            discount = orders.aggregate(total=Sum('discount'))['total'] or 0
            tip_total = tips.aggregate(total=Sum('amount'))['total'] or 0
            payment_total = payments.aggregate(total=Sum('amount'))['total'] or 0
            # Calculate return total from the original order's total price
            return_total = sum(
                return_order.original_order.total_price() 
                for return_order in returns
            )
           
            # Calculate tax total from order items if tax is included in item prices
            tax_total = 0  # Default to 0 if tax calculation is not implemented
            round_off = 0  # Not currently tracked in the Order model
            net_sales = gross - discount
            
            # Calculate number of unique customers
            no_of_people = orders.values('customer').distinct().count()
            no_of_sales = orders.count()
            avg_sale = net_sales / no_of_sales if no_of_sales > 0 else 0
            avg_sale_per_person = net_sales / no_of_people if no_of_people > 0 else 0

            # Prepare response with only essential fields
            response_data = {
                "branchName": request.user.branch.branch_name if hasattr(request.user.branch, 'branch_name') else "Unnamed Branch",
                "grossSales": float(gross),
                "salesReturn": float(return_total),
                "discount": float(discount),
                "directCharges": 0.0,
                "netSales": float(net_sales),
                "otherCharges": 0.0,
                "tax": 0.0,
                "rounding": 0.0,
                "tip": float(tip_total),
                "totalRevenue": float(net_sales + tip_total),
                "payment": float(payment_total),
                "balanceDue": float(max(0, net_sales - payment_total)),
                "netSalesTotal": float(net_sales),
                "numberOfSales": no_of_sales,
                "averageSale": float(avg_sale),
                "numberOfPeople": no_of_people,
                "averageSalePerPerson": float(avg_sale_per_person),
                "asOfTime": datetime.now().isoformat()
            }
            print("🧮 Net Sales:", net_sales)
            print("💸 Payment Total:", payment_total)
            print("📊 Response Summary:", response_data)
            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
