from rest_framework import serializers
from .models import (
    Item, ItemVariant, Tax,
    ItemOptionSet, ItemOptionSetOption
)

class ItemVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVariant
        fields = ['id', 'name', 'value']


class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ['id', 'name', 'percentage']

class ItemOptionSetOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemOptionSetOption
        exclude = ['option_set']  

class ItemOptionSetSerializer(serializers.ModelSerializer):
    options = ItemOptionSetOptionSerializer(many=True)

    class Meta:
        model = ItemOptionSet
        fields = ['id', 'name', 'label', 'min', 'max', 'options']
        

    def create(self, validated_data):
        options_data = validated_data.pop('options')
        option_set = ItemOptionSet.objects.create(**validated_data)
        for option in options_data:
            ItemOptionSetOption.objects.create(option_set=option_set, **option)
        return option_set

    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if options_data:
            # Clear and recreate options
            instance.options.all().delete()
            for option in options_data:
                ItemOptionSetOption.objects.create(option_set=instance, **option)

        return instance
    
class ItemSerializer(serializers.ModelSerializer):
    variants = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ItemVariant.objects.all(),
        many=True,
        required=False
    )
    taxes = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Tax.objects.all(),
        many=True,
        required=False
    )
    optionSets = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ItemOptionSet.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Item
        fields = [
            'id',
            'shortName',
            'longName',
            'description',
            'skuCode',
            'barCode',
            'groupSKUCode',
            'variants',           # dropdown (by name)
            'measuringUnit',
            'category',
            'menus',
            'tags',
            'taxes',              # dropdown (by name)
            'priceIncludesTax',
            'price',
            'optionSets',         # dropdown (by name)
            'displayOrder',
            'categoryDisplayOrder',
        ]