from rest_framework import serializers
from .models import Business


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        exclude = ['device_key', 'pin', 'user_id', 'is_active',
                   'activation_token', 'activation_token_expires', 'forgot_pin_token', 'forgot_pin_token_expires', 'account_number', 'device_label']
        read_only_fields = ['device_key', 'pin', 'user_id']


class DeviceVerificationSerializer(serializers.Serializer):
    device_registration_key = serializers.CharField(
        max_length=20, required=True, source='device_key')
    device_label = serializers.CharField(max_length=100, required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(
                device_key=data['device_key'])
            business.device_label = data['device_label']
            data['business'] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("Invalid device credentials")

class BusinessLoginSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    pin = serializers.CharField(required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(user_id=data['user_id'], pin=data['pin'])
            if not business.is_active:
                raise serializers.ValidationError("Account is not activated.")
            data['business'] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("Invalid User ID or PIN.")

class ResetDeviceSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=8, required=True)
    email = serializers.EmailField(required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(
                account_number=data['account_number'], email=data['email'])
            data['business'] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with the provided details")


class ForgotPinSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(email=data['email'])
            data['business'] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("No account found with the provided email")
        
# class PrimaryContactSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Business
#         fields = [
#             'first_name', 'last_name', 'title',
#             'mobile', 'email'
#         ]


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
