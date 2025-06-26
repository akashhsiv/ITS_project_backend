import bcrypt
from rest_framework import serializers
from .models import User, Contact, Address,Role
from rest_framework import serializers
class PINLoginSerializer(serializers.Serializer):
    user_id = serializers.CharField(
        max_length=6,
        required=True,
        help_text="6-character alphanumeric User ID"
    )
    
    def validate_user_id(self, value):
        if not value.isalnum() or len(value) != 6:
            raise serializers.ValidationError("User ID must be 6 alphanumeric characters.")
        return value



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




class UserCreateSerializer(serializers.ModelSerializer):
    contact = ContactSerializer()
    address = AddressSerializer(required=False)
    
    permitted_stores = serializers.ListField(
    child=serializers.CharField(max_length=100),
    required=False
)

    permitted_brands = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False
    )

    permitted_licenses = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False
    )


    role = serializers.ChoiceField(
        choices=Role.choices,
        required=False,
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
            'role', 'user_level', 'contact', 'address',
            'permitted_licenses', 'permitted_stores', 'permitted_brands',
            'access_profile', 'access_expires_at',
            'can_backdate_orders', 'can_login_offline',
            'allowed_actions', 'all_actions_enabled'
        ]

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must be numeric.")
        return value

    def create(self, validated_data):
        contact_data = validated_data.pop('contact')
        address_data = validated_data.pop('address', None)

        # Get multiple choice values with safe defaults
        permitted_stores = validated_data.pop('permitted_stores', [])
        permitted_brands = validated_data.pop('permitted_brands', [])
        permitted_licenses = validated_data.pop('permitted_licenses', [])

        # Create contact and address
        contact = Contact.objects.create(**contact_data)
        address = Address.objects.create(**address_data) if address_data else None

        # Hash the PIN securely

        # Create user
        user = User.objects.create(
            contact=contact,
            address=address,
            permitted_stores=permitted_stores,
            permitted_brands=permitted_brands,
            permitted_licenses=permitted_licenses,
            **validated_data
        )

        return user