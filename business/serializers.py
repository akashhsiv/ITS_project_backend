from rest_framework import serializers

from .email_utils import send_activation_email
from .models import Business, Branch, Channel
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
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def create(self, validated_data):
        # Get context data
        address = self.context.get("address")
        business = self.context.get("business")
        branch = self.context.get("branch")
        contact = self.context.get("contact")  # Get contact from context
        device_key = generate_key("DC", 8)
        
        # Generate user_id in the format: branchId_firstname_lastname
        first_name = validated_data.get('first_name', '').lower().replace(' ', '_')
        last_name = validated_data.get('last_name', '').lower().replace(' ', '_')
        user_id = f"{branch.id}_{first_name}_{last_name}" if branch else generate_key("ITS", 6)

        # Create user
        user = User(
            user_id=user_id,
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            allowed_actions=validated_data.get('allowed_actions', ['All Actions']),
            permitted_stores=validated_data.get('permitted_stores', ['All Stores']),
            permitted_licenses=validated_data.get('permitted_licenses', ['All Licenses']),
            permitted_brands=validated_data.get('permitted_brands', ['All Brands']),
            business=business,
            branch=branch,
            device_key=device_key,
            address=address,
            contact=contact,
            role='admin'  # Set role to admin for business creator
        )
        user.role = "admin"
        user.save()

        send_activation_email(
            user, self.context.get("request")
        )

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


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class BranchSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=True)
    channels = ChannelSerializer(many=True, required=False)
    business_name = serializers.CharField(source='business.business_name', read_only=True)
    status = serializers.ChoiceField(choices=Branch.STATUS_CHOICES, default='active')
    business = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.all(),
        required=False
    )

    class Meta:
        model = Branch
        fields = [
            'id', 'branch_name', 'branch_code', 'business', 'business_name',
            'status', 'address', 'channels', 'tax_area', 'pricebook',
            'branch_labels', 'tax_id', 'is_active', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'business_name', 'is_default', 'branch_code']
        extra_kwargs = {
            'business': {'required': False}
        }
        
    def validate_branch_name(self, value):
        """Ensure branch name is unique within a business."""
        business = self.context.get('request').user.business
        if Branch.objects.filter(business=business, branch_name=value).exists():
            raise serializers.ValidationError("A branch with this name already exists for this business.")
        return value
        
    def create(self, validated_data):
        address_data = validated_data.pop('address')
        channels_data = validated_data.pop('channels', [])
        
        # Get business from context if not provided
        if 'business' not in validated_data:
            validated_data['business'] = self.context['request'].user.business
            
        # Create address
        address_serializer = AddressSerializer(data=address_data)
        if address_serializer.is_valid(raise_exception=True):
            address = address_serializer.save()
            
        # Generate branch code if not provided
        if 'branch_code' not in validated_data or not validated_data['branch_code']:
            business_prefix = validated_data['business'].business_name[:3].upper()
            branch_count = Branch.objects.filter(
                business=validated_data['business']
            ).count() + 1
            validated_data['branch_code'] = f"{business_prefix}{branch_count:03d}"
            
        # Create branch
        branch = Branch.objects.create(
            **validated_data,
            address=address
        )
        
        # Add channels
        for channel_data in channels_data:
            channel, _ = Channel.objects.get_or_create(
                name=channel_data['name'],
                defaults={'description': channel_data.get('description', '')}
            )
            branch.channels.add(channel)
            
        return branch

    def create(self, validated_data):
        address_data = validated_data.pop('address', None)
        channels_data = validated_data.pop('channels', [])
        
        # Get business from context or use the one in validated_data
        business = validated_data.pop('business', None) or self.context.get('business')
        if not business:
            raise serializers.ValidationError("Business is required")
            
        # Create address
        address_serializer = AddressSerializer(data=address_data)
        if address_serializer.is_valid(raise_exception=True):
            address = address_serializer.save()
        
        # Create branch
        branch = Branch.objects.create(
            **validated_data,
            business=business,
            address=address
        )
        
        # Add channels
        for channel_data in channels_data:
            channel, _ = Channel.objects.get_or_create(
                name=channel_data['name'],
                defaults=channel_data
            )
            branch.channels.add(channel)
            
        return branch

    def update(self, instance, validated_data):
        address_data = validated_data.pop('address', None)
        channels_data = validated_data.pop('channels', None)
        
        # Update address if provided
        if address_data:
            address_serializer = AddressSerializer(
                instance.address, 
                data=address_data, 
                partial=True
            )
            if address_serializer.is_valid(raise_exception=True):
                address_serializer.save()
        
        # Update channels if provided
        if channels_data is not None:
            instance.channels.clear()
            for channel_data in channels_data:
                channel, _ = Channel.objects.get_or_create(
                    name=channel_data['name'],
                    defaults=channel_data
                )
                instance.channels.add(channel)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance


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

        with transaction.atomic():
            # Create business first
            business = Business.objects.create(
                **validated_data, 
                account_number=account_number
            )
            
            # Create default branch first
            default_branch = Branch.objects.create(
                branch_name=f"{business.business_name} - Main Branch",
                branch_code=f"{business.business_name[:3].upper()}001",
                business=business,
                status='active',
                address=Address.objects.create(**address_data) if address_data else None,
                is_default=True
            )
            
            # Create user with the provided address and branch
            user_serializer = BusinessUserSerializer(
                data=business_user_data,
                context={
                    "business": business,
                    "branch": default_branch,  # Pass the created branch to the user
                    "contact": Contact.objects.create(**contact_data) if contact_data else None,
                    "address": default_branch.address,  # Use the branch's address
                    "request": self.context.get("request"),
                }
            )
            user = user_serializer.create(business_user_data)
            
            # Update the branch's address if it wasn't set (for backward compatibility)
            if not default_branch.address and user.address:
                default_branch.address = user.address
                default_branch.save()
                
            return business
        return business