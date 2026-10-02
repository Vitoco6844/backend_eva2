"""Filtros SQL: el rango de precios debe cumplirse en un mismo sector."""
from django.db.models import Exists, OuterRef
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from .models import Event, Sector


class EventFilter(filters.FilterSet):
    nombre = filters.CharFilter(field_name="name", lookup_expr="icontains")
    artista = filters.CharFilter(field_name="artist", lookup_expr="icontains")
    recinto = filters.NumberFilter(field_name="venue_id")
    ciudad = filters.CharFilter(field_name="venue__city", lookup_expr="icontains")
    fecha_desde = filters.DateFilter(field_name="starts_at__date", lookup_expr="gte")
    fecha_hasta = filters.DateFilter(field_name="starts_at__date", lookup_expr="lte")
    precio_min = filters.NumberFilter(method="defer_inventory")
    precio_max = filters.NumberFilter(method="defer_inventory")
    disponibles = filters.BooleanFilter(method="defer_inventory")
    estado = filters.ChoiceFilter(field_name="status", choices=Event.Status.choices)

    class Meta:
        model = Event
        fields = []

    def defer_inventory(self, queryset, name, value):
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        values = self.form.cleaned_data
        minimum, maximum = values.get("precio_min"), values.get("precio_max")
        start, end = values.get("fecha_desde"), values.get("fecha_hasta")
        if (minimum is not None and minimum < 0) or (maximum is not None and maximum < 0):
            raise ValidationError({"precio_min": "Los precios no pueden ser negativos."})
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValidationError({"precio_max": "El maximo debe ser mayor o igual al minimo."})
        if start and end and start > end:
            raise ValidationError({"fecha_hasta": "La fecha final debe ser posterior al inicio."})
        sectors = Sector.objects.with_inventory().filter(event_id=OuterRef("pk"), active=True, current_amount__isnull=False)
        if minimum is not None:
            sectors = sectors.filter(current_amount__gte=minimum, available__gt=0)
        if maximum is not None:
            sectors = sectors.filter(current_amount__lte=maximum, available__gt=0)
        if minimum is not None or maximum is not None:
            queryset = queryset.filter(Exists(sectors))
        if values.get("disponibles") is not None:
            available = Exists(Sector.objects.with_inventory().filter(event_id=OuterRef("pk"), active=True, current_amount__isnull=False, available__gt=0))
            queryset = queryset.filter(available if values["disponibles"] else ~available)
        return queryset
