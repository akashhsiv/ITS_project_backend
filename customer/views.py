from rest_framework import filters, status
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .serializers import CustomerSerializer
from .models import Customer


class CustomerListCreateView(ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    # Optional search and filter support
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['id', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['created_date', 'first_name']


class CustomerDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    lookup_field = 'id'  # Important: since your ID is a CharField primary key

    # Optional: override DELETE to perform a soft delete using `is_blocked`
    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        customer.is_blocked = True
        customer.save()
        return Response({'detail': 'Customer blocked instead of deleted.'}, status=status.HTTP_200_OK)
