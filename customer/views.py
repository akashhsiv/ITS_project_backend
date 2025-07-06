from rest_framework import filters, status
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import CustomerSerializer, CouponCampaignSerializer
from .models import Customer, CouponCampaign

from rest_framework.permissions import IsAuthenticated, AllowAny

class CustomerListCreateView(ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    # Set permissions - AllowAny for GET, IsAuthenticated for POST
    def get_permissions(self):
        if self.request.method == 'POST':
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [AllowAny]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Set the branch to the logged-in user's branch
        if self.request.user.is_authenticated and hasattr(self.request.user, 'branch'):
            serializer.save(branch=self.request.user.branch)
        else:
            # If user has no branch or is not authenticated (shouldn't happen due to permissions)
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("User must be associated with a branch to create customers")

    def get_queryset(self):
        # For authenticated users, filter customers by their branch
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and hasattr(self.request.user, 'branch'):
            return queryset.filter(branch=self.request.user.branch)
        return queryset

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

class CouponCampaignViewSet(viewsets.ModelViewSet):
    queryset = CouponCampaign.objects.all()
    serializer_class = CouponCampaignSerializer


from rest_framework import viewsets
from .models import Company
from .serializers import CompanySerializer

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
