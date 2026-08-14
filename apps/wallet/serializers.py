from decimal import Decimal

from rest_framework import serializers

from .models import ExchangeRate, PaymentMethod, TopUpRequest, Transaction, Wallet


class WalletSerializer(serializers.ModelSerializer):
    balance_uzs = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ("balance_usd", "balance_uzs", "paynet_id")

    def get_balance_uzs(self, obj):
        rate = ExchangeRate.latest()
        if not rate:
            return None
        return round(obj.balance_usd * rate.rate, 2)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ("id", "key", "name", "description", "icon")


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ("id", "kind", "amount", "status", "title", "subtitle", "created_at")


class TopUpRequestSerializer(serializers.ModelSerializer):
    payment_method_key = serializers.SlugRelatedField(
        source="payment_method", slug_field="key", queryset=PaymentMethod.objects.filter(is_active=True)
    )
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal("1"))

    class Meta:
        model = TopUpRequest
        fields = ("id", "amount", "payment_method_key", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")
