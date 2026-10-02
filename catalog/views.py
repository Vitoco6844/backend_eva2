"""CRUD individual protegido; el catalogo publico nunca expone borradores."""
from django.db.models import Prefetch, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CatalogPermission, IsOrganizer
from .models import Venue, Event, Sector
from .serializers import VenueSerializer, EventSerializer, SectorSerializer
from .filters import EventFilter
from .services import delete_resource


def event_queryset():
    return Event.objects.select_related("venue").prefetch_related(
        Prefetch("sectors", queryset=Sector.objects.with_inventory().select_related("event__venue"), to_attr="inventory_sectors")
    )


class VenueViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"\d+"
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [CatalogPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by("-pk") if self.request.user.is_authenticated and self.request.user.is_organizer else qs.filter(active=True)

    def perform_destroy(self, instance):
        delete_resource(instance)


class EventViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"\d+"
    serializer_class = EventSerializer
    permission_classes = [CatalogPermission]
    filterset_class = EventFilter
    queryset = event_queryset()

    def get_queryset(self):
        qs = event_queryset()
        public_catalog = self.request.query_params.get("catalogo") == "true"
        if public_catalog or not (self.request.user.is_authenticated and self.request.user.is_organizer):
            qs = qs.filter(status=Event.Status.PUBLISHED, venue__active=True)
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(artist__icontains=search) | Q(venue__name__icontains=search))
        if self.action == "list" and (public_catalog or not (self.request.user.is_authenticated and self.request.user.is_organizer)):
            qs = qs.filter(starts_at__gt=timezone.now())
        elif self.request.user.is_authenticated and self.request.user.is_organizer:
            qs = qs.order_by("-created_at", "-pk")
        return qs

    def perform_destroy(self, instance):
        delete_resource(instance)

    @extend_schema(responses=SectorSerializer(many=True), tags=["Catalogo"])
    @action(detail=True, methods=["get"], url_path="sectores")
    def sectors(self, request, pk=None):
        event = self.get_object()
        qs = event.sectors.with_inventory().select_related("event__venue")
        if not (request.user.is_authenticated and request.user.is_organizer):
            qs = qs.filter(active=True)
        return Response(SectorSerializer(qs, many=True).data)


class SectorViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"\d+"
    serializer_class = SectorSerializer
    permission_classes = [CatalogPermission]
    queryset = Sector.objects.with_inventory().select_related("event__venue")
    filterset_fields = ["event"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not (self.request.user.is_authenticated and self.request.user.is_organizer):
            qs = qs.filter(active=True, event__status=Event.Status.PUBLISHED, event__venue__active=True)
        else:
            qs = qs.order_by("-pk")
        return qs

    def perform_destroy(self, instance):
        delete_resource(instance)
