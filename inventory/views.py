from rest_framework import viewsets
from .models import (
    Item, ItemVariant, Tax,
    ItemOptionSet, ItemOptionSetOption
)
from .serializers import (
    ItemSerializer, ItemVariantSerializer, TaxSerializer,
    ItemOptionSetSerializer, ItemOptionSetOptionSerializer
)


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('id')
    serializer_class = ItemSerializer


class ItemVariantViewSet(viewsets.ModelViewSet):
    queryset = ItemVariant.objects.all().order_by('id')
    serializer_class = ItemVariantSerializer


class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.all().order_by('id')
    serializer_class = TaxSerializer


class ItemOptionSetViewSet(viewsets.ModelViewSet):
    queryset = ItemOptionSet.objects.all().order_by('id')
    serializer_class = ItemOptionSetSerializer


class ItemOptionSetOptionViewSet(viewsets.ModelViewSet):
    queryset = ItemOptionSetOption.objects.all().order_by('id')
    serializer_class = ItemOptionSetOptionSerializer 
