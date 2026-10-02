"""Contratos de entrada estrictos y representaciones de compras calculadas."""
from rest_framework import serializers
from web.api import StrictInputMixin
from .models import Purchase, PurchaseLine, Ticket, PurchaseTransition


class AddItemSerializer(StrictInputMixin, serializers.Serializer):
    sector = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class QuantitySerializer(StrictInputMixin, serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class CheckoutSerializer(StrictInputMixin, serializers.Serializer):
    checkout_key = serializers.UUIDField()
    version = serializers.IntegerField(min_value=0)
    quote = serializers.CharField(max_length=2000)


class PaymentSerializer(StrictInputMixin, serializers.Serializer):
    result = serializers.ChoiceField(choices=["approved", "declined"])


class DirectPaymentSerializer(PaymentSerializer):
    purchase = serializers.UUIDField()


class StatusSerializer(StrictInputMixin, serializers.Serializer):
    status = serializers.ChoiceField(choices=Purchase.Status.choices)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class AdmissionSerializer(StrictInputMixin, serializers.Serializer):
    ticket = serializers.UUIDField()
    event = serializers.IntegerField(min_value=1)


class TicketSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "ordinal", "status", "issued_at", "used_at"]


class MyTicketSerializer(TicketSerializer):
    event_name = serializers.CharField(source="line.price.sector.event.name", read_only=True)
    sector_name = serializers.CharField(source="line.price.sector.name", read_only=True)
    starts_at = serializers.DateTimeField(source="line.price.sector.event.starts_at", read_only=True)
    purchase = serializers.UUIDField(source="line.purchase_id", read_only=True)

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ["event_name", "sector_name", "starts_at", "purchase"]


class LineSerializer(serializers.ModelSerializer):
    event = serializers.IntegerField(source="price.sector.event_id", read_only=True)
    event_name = serializers.CharField(source="price.sector.event.name", read_only=True)
    starts_at = serializers.DateTimeField(source="price.sector.event.starts_at", read_only=True)
    venue = serializers.CharField(source="price.sector.event.venue.name", read_only=True)
    sector_name = serializers.CharField(source="price.sector.name", read_only=True)
    unit_price = serializers.IntegerField(source="price.amount", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    tickets = TicketSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseLine
        fields = ["id", "event", "event_name", "starts_at", "venue", "sector_name", "unit_price", "quantity", "subtotal", "tickets"]


class TransitionSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = PurchaseTransition
        fields = ["previous_status", "new_status", "actor_name", "reason", "created_at"]


class PurchaseSerializer(serializers.ModelSerializer):
    buyer = serializers.CharField(source="user.username", read_only=True)
    total = serializers.IntegerField(read_only=True)
    lines = LineSerializer(many=True, read_only=True)
    transitions = TransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = ["id", "buyer", "status", "total", "created_at", "paid_at", "cancelled_at", "lines", "transitions"]


class CartRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sector = serializers.IntegerField()
    event = serializers.IntegerField()
    event_name = serializers.CharField()
    sector_name = serializers.CharField()
    starts_at = serializers.DateTimeField()
    venue = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.IntegerField()
    price_id = serializers.IntegerField(allow_null=True)
    available = serializers.IntegerField()
    sellable = serializers.BooleanField()
    subtotal = serializers.IntegerField()


class CartSerializer(serializers.Serializer):
    version = serializers.IntegerField()
    items = CartRowSerializer(many=True)
    total = serializers.IntegerField()
    quote = serializers.CharField()
