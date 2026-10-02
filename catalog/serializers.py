"""Campos publicos y validacion de formularios individuales del catalogo."""
import uuid
from django.templatetags.static import static
from rest_framework import serializers
from web.api import StrictInputMixin
from .models import Venue, Event, Sector
from . import services


class VenueSerializer(StrictInputMixin, serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "address", "city", "active"]
        read_only_fields = ["id"]

    def create(self, data):
        return services.save_venue(data)

    def update(self, instance, data):
        return services.save_venue(data, instance)


class SectorSerializer(StrictInputMixin, serializers.ModelSerializer):
    price = serializers.IntegerField(min_value=1, max_value=100000000, write_only=True)
    current_amount = serializers.IntegerField(read_only=True)
    current_price_id = serializers.IntegerField(read_only=True)
    available = serializers.IntegerField(read_only=True)
    committed = serializers.IntegerField(read_only=True)
    event_name = serializers.CharField(source="event.name", read_only=True)

    class Meta:
        model = Sector
        fields = ["id", "event", "event_name", "name", "capacity", "active", "price", "current_amount", "current_price_id", "available", "committed"]
        read_only_fields = ["id"]
        extra_kwargs = {"capacity": {"max_value": 1000000, "min_value": 0}}

    def create(self, data):
        return services.save_sector(data)

    def update(self, instance, data):
        return services.save_sector(data, instance)


class EventSerializer(StrictInputMixin, serializers.ModelSerializer):
    venue_name = serializers.CharField(source="venue.name", read_only=True)
    city = serializers.CharField(source="venue.city", read_only=True)
    venue_address = serializers.CharField(source="venue.address", read_only=True)
    cover_url = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    price_from = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["id", "name", "slug", "artist", "description", "starts_at", "venue", "venue_name", "city", "venue_address", "status", "image", "artwork", "cover_url", "sectors", "price_from", "available"]
        read_only_fields = ["id", "slug"]

    def validate_image(self, image):
        if image and image.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La imagen no debe superar 5 MB.")
        if image and image.image.format not in ["JPEG", "PNG", "WEBP"]:
            raise serializers.ValidationError("Usa una imagen JPG, PNG o WebP.")
        if image:
            # La extension la decide el formato verificado, nunca el nombre enviado.
            extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image.image.format]
            image.name = f"{uuid.uuid4().hex}.{extension}"
        return image

    def get_cover_url(self, obj) -> str:
        return obj.image.url if obj.image else static(f"images/{obj.artwork}.png")

    def _sectors(self, obj):
        cached = getattr(obj, "inventory_sectors", None)
        return cached if cached is not None else list(obj.sectors.with_inventory().select_related("event"))

    def get_sectors(self, obj) -> list:
        return SectorSerializer([s for s in self._sectors(obj) if s.active], many=True).data

    def get_price_from(self, obj) -> int | None:
        prices = [s.current_amount for s in self._sectors(obj) if s.active and s.available > 0 and s.current_amount]
        return min(prices) if prices else None

    def get_available(self, obj) -> int:
        return sum(s.available for s in self._sectors(obj) if s.active)

    def create(self, data):
        return services.save_event(data)

    def update(self, instance, data):
        return services.save_event(data, instance)
