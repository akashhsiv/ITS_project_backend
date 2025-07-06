from rest_framework import serializers
import cloudinary
from users.models import Address
from .models import Customer, Membership, LoyaltyInfo, Company
from .models import CouponCampaign, Discount


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id',
            'address_line1',
            'city',
            'state',
            'country',
            'zip_code',
            'landmark',
            'latitude',
            'longitude',
        ]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ['name', 'start_date', 'end_date']


class LoyaltyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyInfo
        fields = [
            'points',
            'reserved_points',
            'points_ending_this_month',
            'points_ending_next_month',
        ]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['name', 'company_id', 'tax_id']


class CustomerSerializer(serializers.ModelSerializer):
    membership = MembershipSerializer(required=False)
    loyalty_info = LoyaltyInfoSerializer(required=False)
    address_data = AddressSerializer(write_only=True, required=False)
    addresses = AddressSerializer(read_only=True)

    company_data = CompanySerializer(write_only=True, required=False)
    company = CompanySerializer(read_only=True)
    
    pan_card_front = serializers.ImageField(required=False, allow_null=True, write_only=True)
    pan_card_back  = serializers.ImageField(required=False, allow_null=True, write_only=True)


    class Meta:
        model = Customer
        fields = [
            'id',
            'branch',
            'first_name',
            'last_name',
            'phone_number',
            'emails',
            'gender',
            'dob',
            'anniversary_date',
            'tax_id',
            'secondary_tax_id',
            'tax_state_code',
            'is_blocked',
            'created_date',
            'pan_card_front',
            'pan_card_back',
            'company_data',
            'company',
            'address_data',
            'addresses',
            'membership',
            'loyalty_info',
        ]

    def create(self, validated_data):
        membership_data = validated_data.pop('membership', None)
        loyalty_data = validated_data.pop('loyalty_info', None)
        address_data = validated_data.pop('address_data', None)
        company_data = validated_data.pop('company_data', None)

        if company_data:
            company, _ = Company.objects.get_or_create(**company_data)
            validated_data['company'] = company

        if address_data:
            address = Address.objects.create(**address_data)
            validated_data['addresses'] = address

        customer = Customer.objects.create(**validated_data)

        if membership_data:
            Membership.objects.create(customer=customer, **membership_data)

        if loyalty_data:
            LoyaltyInfo.objects.create(customer=customer, **loyalty_data)

        return customer
    def to_representation(self, instance):
        
        data = super().to_representation(instance)

        if instance.pan_card_front:
            data['pan_card_front'] = instance.pan_card_front.url

        if instance.pan_card_back:
            data['pan_card_back'] = instance.pan_card_back.url
        return data
    
    def update(self, instance, validated_data):
        membership_data = validated_data.pop('membership', None)
        loyalty_data = validated_data.pop('loyalty_info', None)
        address_data = validated_data.pop('address_data', None)
        company_data = validated_data.pop('company_data', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if address_data:
            if instance.addresses:
                for attr, value in address_data.items():
                    setattr(instance.addresses, attr, value)
                instance.addresses.save()
            else:
                address = Address.objects.create(**address_data)
                instance.addresses = address

        if company_data:
            company, _ = Company.objects.get_or_create(**company_data)
            instance.company = company

        instance.save()

        if membership_data:
            if hasattr(instance, 'membership'):
                for attr, value in membership_data.items():
                    setattr(instance.membership, attr, value)
                instance.membership.save()
            else:
                Membership.objects.create(customer=instance, **membership_data)

        if loyalty_data:
            if hasattr(instance, 'loyalty_info'):
                for attr, value in loyalty_data.items():
                    setattr(instance.loyalty_info, attr, value)
                instance.loyalty_info.save()
            else:
                LoyaltyInfo.objects.create(customer=instance, **loyalty_data)

        return instance



class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ['discountCode']

class CouponCampaignSerializer(serializers.ModelSerializer):
    discounts = DiscountSerializer(many=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())

    class Meta:
        model = CouponCampaign
        fields = [
            'couponProvider', 'couponCode', 'startDate', 'expiryDate',
            'campaignName', 'discounts', 'customer'
        ]

    def create(self, validated_data):
        discount_data = validated_data.pop('discounts')
        campaign = CouponCampaign.objects.create(**validated_data)
        for discount in discount_data:
            d, _ = Discount.objects.get_or_create(**discount)
            campaign.discounts.add(d)
        return campaign



from rest_framework import serializers
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
