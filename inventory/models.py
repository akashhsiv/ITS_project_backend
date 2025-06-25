from django.db import models


class Tax(models.Model):
    name = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"


class ItemVariant(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}: {self.value}"


class ItemOptionSet(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., "Item Toppings"
    label = models.CharField(max_length=100, blank=True, null=True)
    min = models.PositiveIntegerField(default=0)
    max = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.label or self.name


class ItemOptionSetOption(models.Model):
    option_set = models.ForeignKey(ItemOptionSet, related_name='options', on_delete=models.CASCADE)
    option_id = models.CharField(max_length=100, unique=True)  # "id*" field
    name = models.CharField(max_length=100)  # e.g., "Cheese"
    displayOrder = models.PositiveIntegerField(default=0)
    skuCode = models.CharField(max_length=100)
    isDefault = models.BooleanField(default=False)
    measuringUnit = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name


class Item(models.Model):
    shortName = models.CharField(max_length=100)
    longName = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    skuCode = models.CharField(max_length=100, unique=True)
    barCode = models.CharField(max_length=100, blank=True, null=True)
    groupSKUCode = models.CharField(max_length=100, blank=True, null=True)

    variants = models.ManyToManyField(ItemVariant, blank=True)
    measuringUnit = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    menus = models.JSONField(default=list, blank=True)  
    tags = models.JSONField(default=list, blank=True)  

    taxes = models.ManyToManyField(Tax, blank=True)

    priceIncludesTax = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    optionSets = models.ManyToManyField(ItemOptionSet, blank=True)

    displayOrder = models.PositiveIntegerField(default=0)
    categoryDisplayOrder = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.shortName
