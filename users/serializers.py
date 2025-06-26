from business.models import Business
from .models import User
from django.db import transaction
import random
import string
from rest_framework import serializers

from users.email_utils import send_activation_email
from .models import User, Contact, Address
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import User


def generate_key(prefix, length=6):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class ContactSerializer(serializers.ModelSerializer):
    title = serializers.ChoiceField(
        choices=Contact.TitleChoices.choices,
        required=False
    )

    class Meta:
        model = Contact
        fields = ['email', 'phone', 'title']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['address_line1', 'city', 'state', 'zip_code', 'country']


class UserSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    address = AddressSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "user_id",
            "first_name",
            "last_name",
            "role",
            "user_level",
            "permitted_stores",
            "permitted_licenses",
            "permitted_brands",
            "allowed_actions",
            "all_actions_enabled",
            "can_backdate_orders",
            "can_login_offline",
            "account_number",
            "device_key",
            "device_label",
            "access_profile",
            "access_expires_at",
            "contact",
            "address",
            "business",           # optional if needed
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "user_id", "device_key",
                            "business", "created_at", "updated_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(required=False)
    address = AddressSerializer(required=False)

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            "password": {"read_only": True},
        }

    def create(self, validated_data):
        contact_data = validated_data.pop("contact", None)
        address_data = validated_data.pop("address", None)

        request = self.context.get("request")
        print("Creating user with validated data:", request)
        business = getattr(request.user, "business", None) if request else None
        print("Business associated with request:", business)

        with transaction.atomic():
            contact = Contact.objects.create(
                **contact_data) if contact_data else None
            address = Address.objects.create(
                **address_data) if address_data else None

            user = User.objects.create(
                contact=contact,
                address=address,
                business=business,
                device_key=generate_key("DC", 8),
                **validated_data
            )
            user.save()

            send_activation_email(user, self.context.get("request"))

        return user


class UserIDTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        print("Validating UserIDTokenObtainPairSerializer with attrs:", attrs)
        data = super().validate(attrs)

        user = getattr(self, "user", None)
        if user is None:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError(
                "Your account is not activated yet.")

        if user.business and not user.business.is_active:
            raise serializers.ValidationError(
                "Your business is not activated yet.")

        data["role"] = user.role
        data["first_name"] = user.first_name
        return data


class DeviceVerificationSerializer(serializers.Serializer):
    device_registration_key = serializers.CharField(
        max_length=20, write_only=True)
    device_label = serializers.CharField(max_length=100, write_only=True)

    def validate(self, attrs):
        """
        Validate that the (device_key, pin) pair matches a User.
        Attach the user instance so the ViewSet can use it later.
        """
        key = attrs["device_registration_key"]

        try:
            user = User.objects.get(device_key=key)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid device key")

        attrs["user"] = user
        return attrs


class ResetDeviceSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=8, required=True)
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        account_number = attrs["account_number"]
        email = attrs["email"]

        try:
            business = Business.objects.get(
                account_number=account_number,
            )
        except Business.DoesNotExist:
            raise serializers.ValidationError(
                "No business found with the given account number and email"
            )

        try:
            user = User.objects.get(
                business=business,
                contact__email=email
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No user found for this business and email"
            )

        attrs["business"] = business
        attrs["user"] = user
        return attrs


class ForgotPinSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        try:
            user = User.objects.get(contact__email=data["email"])
            data["user"] = user
            return data
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with the provided email"
            )

class ChangePinSerializer(serializers.Serializer):
    old_pin = serializers.CharField(max_length=10, write_only=True)
    new_pin = serializers.CharField(max_length=10, write_only=True)

    # --- helpers -----------------------------------------------------------
    def _get_user(self):
        request = self.context.get("request")
        if request is None or not hasattr(request, "user"):
            raise serializers.ValidationError("Request context (user) is missing")
        return request.user
    # -----------------------------------------------------------------------

    def validate_old_pin(self, value):
        user = self._get_user()
        # If you store PIN hashed in password field:
        if not user.check_password(value):
            raise serializers.ValidationError("Old PIN is incorrect")
        return value

    def validate_new_pin(self, value):
        if len(value) < 4:
            raise serializers.ValidationError("PIN must be at least 4 digits")
        if not value.isdigit():
            raise serializers.ValidationError("PIN must be numeric")
        return value

    def save(self, **kwargs):
        user = self._get_user()
        user.set_password(self.validated_data["new_pin"])  # hashes the new PIN
        user.save(update_fields=["password"])
        return user
