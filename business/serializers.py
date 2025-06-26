from rest_framework import serializers

from .email_utils import send_activation_email
from .models import Business
from users.models import User, Address, Contact
from users.serializers import ContactSerializer, AddressSerializer
from django.db import transaction
import random
import string


def generate_key(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class BusinessUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]

    def create(self, validated_data):
        address = self.context.get("address")
        contact = self.context.get("contact")
        business = self.context.get("business")
        device_key = generate_key("DC", 8)
        user_id = generate_key("ITS", 6)

        user = User(**validated_data, allowed_actions=['All Actions'], permitted_stores=["All Stores"], permitted_licenses=["All Licenses"], permitted_brands=["All Brands"],
                    business=business, device_key=device_key, user_id=user_id, address=address, contact=contact)
        user.role = "admin"
        user.save()

        return user


class UserReadSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    address = AddressSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "role",
            "contact", "address"
        ]


class BusinessReadSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id", "business_name", "brand_name", "business_type",
            "is_active", "created_at", "user"
        ]

    def get_user(self, obj):
        primary_user = obj.users.order_by("created_at").first()
        if primary_user:
            return UserReadSerializer(primary_user).data
        return None


class BusinessCreateUpdateSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(write_only=True, required=False)
    address = AddressSerializer(write_only=True, required=False)
    business_user = BusinessUserSerializer(write_only=True)   # required

    class Meta:
        model = Business
        fields = (
            "business_name", "brand_name", "business_type",
            "contact", "address", "business_user",
        )

    def create(self, validated_data):
        # pop nested chunks
        contact_data = validated_data.pop("contact", None)
        address_data = validated_data.pop("address", None)
        business_user_data = validated_data.pop("business_user")
        account_number = str(random.randint(10000000, 99999999))

        # create nested objects up-front
        contact = Contact.objects.create(
            **contact_data) if contact_data else None
        address = Address.objects.create(
            **address_data) if address_data else None

        with transaction.atomic():
            business = Business.objects.create(
                **validated_data, account_number=account_number
            )
            BusinessUserSerializer(
                context={
                    "business": business,
                    "contact": contact,
                    "address": address,
                    "request": self.context.get("request"),
                }
            ).create(business_user_data)
        return business