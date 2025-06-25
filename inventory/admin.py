from django.contrib import admin
from .models import (
    Item, Tax, ItemVariant, ItemOptionSet, ItemOptionSetOption
)

admin.site.register(Item)
admin.site.register(Tax)
admin.site.register(ItemVariant)
admin.site.register(ItemOptionSet)
admin.site.register(ItemOptionSetOption)
