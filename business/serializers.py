from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Business

class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        exclude = ['device_key', 'pin', 'user_id', 'is_active', 'activation_token', 'activation_token_expires']
        read_only_fields = ['device_key', 'pin', 'user_id']






























# class BusinessNameSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Business
#         fields = ['business_name', 'brand_name']


# class BusinessAddressSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Business
#         fields = [
#             'address_line', 'city', 'state', 'zip_code',
#             'country', 'latitude', 'longitude'
#         ]


# class BusinessTypeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Business
#         fields = ['business_type']


class DeviceVerificationSerializer(serializers.Serializer):
    device_registration_key = serializers.CharField(max_length=20, required=True, source='device_key')
    pin = serializers.CharField(max_length=6, required=True)
    
    def validate(self, data):
        try:
            business = Business.objects.get(device_key=data['device_key'], pin=data['pin'])
            data['business'] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("Invalid device credentials")


class ResetDeviceSerializer(serializers.Serializer):
    account_number = serializers.IntegerField(required=True)
    email = serializers.EmailField(required=True)
    
    def validate(self, data):
        try:
            business = Business.objects.get(id=data['account_number'], email=data['email'])
            data['business'] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("No account found with the provided details")


# class PrimaryContactSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Business
#         fields = [
#             'first_name', 'last_name', 'title',
#             'mobile', 'email'
#         ]
