from rest_framework import serializers

class NamedAmountSerializer(serializers.Serializer):
    name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class TipSummarySerializer(serializers.Serializer):
    user = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class PaymentSummarySerializer(serializers.Serializer):
    mode = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class ItemSummarySerializer(serializers.Serializer):
    skuCode = serializers.CharField()
    itemName = serializers.CharField()
    brandName = serializers.CharField()
    accountName = serializers.CharField()
    categoryName = serializers.CharField()
    subCategory = serializers.CharField()
    itemNature = serializers.CharField()
    type = serializers.CharField()
    measuringUnit = serializers.CharField()
    itemTotalDiscountAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    itemTotalNetAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    itemTotalQty = serializers.IntegerField()
    itemTotalgrossAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    itemTotaltaxAmount = serializers.DecimalField(max_digits=10, decimal_places=2)

class SessionSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    netSaleAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    noOfSales = serializers.IntegerField()
    avgSaleAmount = serializers.DecimalField(max_digits=10, decimal_places=2)

class ChannelSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    netSaleAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    noOfSales = serializers.IntegerField()
    avgSaleAmount = serializers.DecimalField(max_digits=10, decimal_places=2)

class AccountChannelSerializer(serializers.Serializer):
    account = serializers.CharField()
    channel = ChannelSummarySerializer(many=True)

class CashSummarySerializer(serializers.Serializer):
    grossAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    returnAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discountTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    directChargeTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    netAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    chargeTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    taxTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    roundOffTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    tipTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    paymentTotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    balanceAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    costOfGoodsSold = serializers.DecimalField(max_digits=10, decimal_places=2)
    marginOnNetSales = serializers.DecimalField(max_digits=10, decimal_places=2)

    discounts = NamedAmountSerializer(many=True)
    categories = NamedAmountSerializer(many=True)
    charges = NamedAmountSerializer(many=True)
    taxes = NamedAmountSerializer(many=True)
    tips = TipSummarySerializer(many=True)
    payments = PaymentSummarySerializer(many=True)

    noOfSales = serializers.IntegerField()
    avgSaleAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    noOfPeople = serializers.IntegerField()
    avgSaleAmountPerPerson = serializers.DecimalField(max_digits=10, decimal_places=2)
    asOfTime = serializers.CharField()

    sessionSummary = SessionSummarySerializer(many=True)
    channelSummary = ChannelSummarySerializer(many=True)
    costs = NamedAmountSerializer(many=True)
    items = ItemSummarySerializer(many=True)
    accounts = NamedAmountSerializer(many=True)
    accountsWiseChannels = AccountChannelSerializer(many=True)
