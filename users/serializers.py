from business.models import Business
from .models import User
from django.db import transaction
import random
import string
from django.utils.crypto import get_random_string
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
        fields = ['address_line1', 'city', 'state', 'zip_code', 'country', 'landmark', 'latitude', 'longitude']


class UserSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(source='branch', read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "user_id",
            "first_name",
            "last_name",
            "role",
            "branch_id",
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
            "business", 
            "branch",          # optional if needed
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "user_id", "device_key",
                            "business", "created_at", "updated_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(required=True)
    address = AddressSerializer(required=False)
    user_id = serializers.CharField(required=True, help_text="User ID (e.g., employee_id or custom ID)")

    class Meta:
        model = User
        fields = [
            'user_id', 'first_name', 'last_name', 'role',
            'contact', 'address', 'is_active'
        ]
        extra_kwargs = {
            'password': {'read_only': True},
            'is_active': {'read_only': True},
        }
        
    def validate(self, attrs):
        contact_data = attrs.get('contact', {})
            
        # Ensure email is provided in contact data
        if not contact_data.get('email'):
            raise serializers.ValidationError({"contact": {"email": "This field is required."}})
            
        return attrs

    def validate_branch_code(self, value):
        """Validate that the branch exists and is active."""
        from business.models import Branch
        try:
            return Branch.objects.get(branch_code=value, is_active=True)
        except Branch.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive branch code.")

    def validate(self, data):
        """
        Ensure the requesting user has permission to create a user.
        The new user will be assigned to the same branch as the requesting user.
        """
        request = self.context.get('request')
        user_role = getattr(request.user, 'role', '').lower()
        
        # Only admin users or users with a branch can create users
        if user_role != 'admin' and not hasattr(request.user, 'branch'):
            raise serializers.ValidationError({
                'non_field_errors': ['You must be an admin or associated with a branch to create a user.']
            })
            
        # Ensure the requesting user has a branch (unless they're an admin)
        if user_role != 'admin' and not request.user.branch:
            raise serializers.ValidationError({
                'non_field_errors': ['Your account is not associated with any branch. Please contact support.']
            })
            
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        contact_data = validated_data.pop('contact')
        address_data = validated_data.pop('address', None)
        user_id = validated_data.pop('user_id')
        
        # Get branch and business from the requesting user
        branch = request.user.branch
        business = branch.business if branch else None
        
        if not branch:
            raise serializers.ValidationError({
                'non_field_errors': ['Cannot create user: No branch is associated with your account.']
            })
        
        # Generate a random password that will be reset on first login
        password = get_random_string(12)
        
        with transaction.atomic():
            # Create contact and address
            contact = Contact.objects.create(**contact_data)
            address = Address.objects.create(**address_data) if address_data else None
            
            # Create the user using the manager's create_user method
            user_data = {
                'first_name': validated_data.pop('first_name', ''),
                'last_name': validated_data.pop('last_name', ''),
                'role': validated_data.pop('role', 'cashier').lower(),
                'business': business,
                'branch': branch,  # Include the branch here
                'contact': contact,
                'address': address,
                'device_key': generate_key("DC", 8),
                'is_active': False,  # User needs to activate via email
                **validated_data
            }
            
            # Create the user with the manager
            user = User.objects.create_user(
                user_id=user_id,
                pin=password,  # Use pin instead of password
                **user_data
            )
            
            # Send activation email
            if contact.email:
                user.generate_activation_token()
                send_activation_email(user, request)
            
            return user


class UserIDTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Custom fields for user login
    user_id = serializers.CharField(
        max_length=50,
        write_only=True,
        required=True,
        help_text="User's unique ID (format: branchid_username)"
    )
    pin = serializers.CharField(
        max_length=10,
        write_only=True,
        required=True,
        help_text="User's PIN code"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the default username and password fields
        self.fields.pop("password", None)
        self.fields.pop(self.username_field, None)

    def validate(self, attrs):
        print("\n=== Login Attempt ===")
        print(f"Received data: {attrs}")
        
        device_key = attrs.pop("device_key", None)
        pin = attrs.pop("pin", None)
        
        if not device_key or not pin:
            print("Error: Missing device_key or pin in request")
            raise serializers.ValidationError("Both device_key and pin are required")
            
        print(f"Looking for user with device_key: {device_key}")
        
        try:
            # Find user by device key
            user = User.objects.get(device_key=device_key)
            print(f"Found user: {user.user_id} (ID: {user.id})")
            print(f"User is_active: {user.is_active}")
            print(f"User business active: {getattr(user.business, 'is_active', 'No business')}")
            
            # Verify the PIN
            print("Verifying PIN...")
            if not user.check_password(pin):
                print("Error: Invalid PIN")
                raise serializers.ValidationError("Invalid PIN")
                
            print("PIN verified successfully")
                
            # Check account and business status
            print("Checking account status...")
            if not user.is_active:
                print("Error: User account is not active")
                raise serializers.ValidationError("Your account is not activated yet.")

            if user.business:
                print(f"Business status - ID: {user.business.id}, Active: {user.business.is_active}")
                if not user.business.is_active:
                    print("Error: Business is not active")
                    raise serializers.ValidationError("Your business is not activated yet.")
            else:
                print("Warning: User has no associated business")
                
            # Generate tokens
            refresh = self.get_token(user)
            
            # Prepare response data
            data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                "user_id": user.user_id,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.contact.email if hasattr(user, 'contact') and user.contact else None,
                "business_id": user.business.id if user.business else None,
                "branch_id": user.branch.id if user.branch else None,
                "branch_name": user.branch.branch_name if user.branch else None,
                "device_label": user.device_label,
            }
            
            print("Login successful!")
            print(f"Generated tokens for user: {user.user_id}")
            return data
            
        except User.DoesNotExist:
            print(f"Error: No user found with device_key: {device_key}")
            raise serializers.ValidationError("Invalid device registration key")
            
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Login error for device {device_key}: {str(e)}")
            raise


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
        user.save(update_fields=["pin"])
        return user

#Go offline serializer
class GoOfflineSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)  # User ID to identify the user
    pin = serializers.CharField(required=True, max_length=6)  # PIN for authentication
    
#Account serializer
class AccountSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)  # User ID to identify the user
    
    

 