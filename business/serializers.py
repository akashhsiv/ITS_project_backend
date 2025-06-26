from rest_framework import serializers

from users.emai_utils import send_activation_email
from .models import Business
from users.models import User, Address, Contact
from django.db import transaction


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"


class FirstUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]

    def create(self, validated_data):
        address = self.context.get("address")
        contact = self.context.get("contact")

        user = User(**validated_data, address=address, contact=contact)
        user.role = "admin"
        user.save()

        send_activation_email(user, self.context.get("request"))

        return user


class BusinessSerializer(serializers.ModelSerializer):
    contact = ContactSerializer()
    address = AddressSerializer()
    first_user = FirstUserSerializer(write_only=True)

    class Meta:
        model = Business
        fields = [
            "business_name",
            "brand_name",
            "business_type",
            "contact",
            "address",
            "first_user",
        ]

    def create(self, validated_data):
        # Properly pop these so they aren't passed twice
        address_data = validated_data.pop("address", None)
        contact_data = validated_data.pop("contact", None)
        first_user_data = validated_data.pop("first_user")

        print("Address Data:", address_data)
        print("Contact Data:", contact_data)

        # Create nested instances
        address = Address.objects.create(**address_data) if address_data else None
        contact = Contact.objects.create(**contact_data) if contact_data else None

        print("Address Created:", address)
        print("Contact Created:", contact)

        with transaction.atomic():
            business = Business.objects.create(**validated_data)
            first_user_data["business"] = business
            FirstUserSerializer(
                context={"business": business, "address": address, "contact": contact}
            ).create(first_user_data)

        return business


class DeviceVerificationSerializer(serializers.Serializer):
    device_registration_key = serializers.CharField(
        max_length=20, required=True, source="device_key"
    )
    device_label = serializers.CharField(max_length=100, required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(device_key=data["device_key"])
            business.device_label = data["device_label"]
            data["business"] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("Invalid device credentials")


class BusinessLoginSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    pin = serializers.CharField(required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(user_id=data["user_id"], pin=data["pin"])
            if not business.is_active:
                raise serializers.ValidationError("Account is not activated.")
            data["business"] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError("Invalid User ID or PIN.")


class ResetDeviceSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=8, required=True)
    email = serializers.EmailField(required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(
                account_number=data["account_number"], email=data["email"]
            )
            data["business"] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with the provided details"
            )


class ForgotPinSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        try:
            business = Business.objects.get(email=data["email"])
            data["business"] = business
            return data
        except Business.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with the provided email"
            )


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
