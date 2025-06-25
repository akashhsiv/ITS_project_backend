from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ItemViewSet, ItemVariantViewSet, TaxViewSet,
    ItemOptionSetViewSet
)
router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'variants', ItemVariantViewSet)
router.register(r'taxes', TaxViewSet)
router.register(r'option-sets', ItemOptionSetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]