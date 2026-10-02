"""Escrituras del catalogo coordinadas con checkout, pago y cancelacion."""
import uuid

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import NotFound, ValidationError

from web.api import Conflict
from .models import Venue, Event, Sector, Price


def has_orders(sector_ids):
    from sales.models import PurchaseLine
    return PurchaseLine.objects.filter(price__sector_id__in=sector_ids).exists()


def lock_inventory(sector_ids):
    """Orden unico: recintos, eventos y sectores. Debe ejecutarse dentro de atomic."""
    ids = sorted(set(sector_ids))
    mapping = list(Sector.objects.filter(pk__in=ids).values("id", "event_id", "event__venue_id"))
    if len(mapping) != len(ids):
        raise NotFound("Una localidad ya no existe.")
    venue_ids = sorted({row["event__venue_id"] for row in mapping})
    event_ids = sorted({row["event_id"] for row in mapping})
    list(Venue.objects.select_for_update().filter(pk__in=venue_ids).order_by("pk"))
    events = list(Event.objects.select_for_update().filter(pk__in=event_ids).order_by("pk"))
    if any(event.venue_id not in venue_ids for event in events):
        raise Conflict("El recinto cambio. Revisa la seleccion y vuelve a intentar.", "catalog_changed")
    locked = list(Sector.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    if len(locked) != len(ids):
        raise NotFound("Una localidad ya no existe.")
    return {sector.pk: sector for sector in Sector.objects.with_inventory().filter(pk__in=ids).select_related("event__venue")}


def assert_sellable(sector):
    if not sector.active or not sector.event.is_sellable or not sector.current_price_id:
        raise Conflict("Esta localidad ya no esta a la venta.", "not_sellable")


@transaction.atomic
def save_venue(data, instance=None):
    if instance:
        instance = Venue.objects.select_for_update().get(pk=instance.pk)
        events = list(instance.events.select_for_update().order_by("pk"))
        protected = has_orders(Sector.objects.filter(event__in=events).values("pk"))
        if protected and any(key in data and data[key] != getattr(instance, key) for key in ["name", "address", "city"]):
            raise Conflict("El recinto tiene compras asociadas. Conserva sus datos historicos o crea otro recinto.", "historical_record")
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
    return Venue.objects.create(**data)


@transaction.atomic
def save_event(data, instance=None):
    venue_ids = {data["venue"].pk} if "venue" in data else set()
    if instance:
        venue_ids.add(instance.venue_id)
    list(Venue.objects.select_for_update().filter(pk__in=venue_ids).order_by("pk"))
    if instance:
        instance = Event.objects.select_for_update().get(pk=instance.pk)
        if instance.venue_id not in venue_ids:
            raise Conflict("El evento cambio. Recarga el formulario.", "catalog_changed")
        if has_orders(instance.sectors.values("pk")):
            for field in ["name", "artist", "starts_at", "venue"]:
                if field in data and data[field] != getattr(instance, field):
                    raise Conflict("No puedes cambiar nombre, artista, fecha o recinto de un evento con compras. Su historial esta protegido.", "historical_record")
    starts_at = data.get("starts_at", instance.starts_at if instance else None)
    target_status = data.get("status", instance.status if instance else Event.Status.DRAFT)
    if (not instance or "starts_at" in data) and starts_at <= timezone.now():
        raise ValidationError({"starts_at": "Selecciona una fecha futura."})
    if target_status == Event.Status.PUBLISHED:
        if not instance or not instance.sectors.filter(active=True, prices__isnull=False).exists():
            raise ValidationError({"status": "Agrega al menos una localidad con tarifa antes de publicar."})
        venue = data.get("venue", instance.venue)
        if not venue.active or starts_at <= timezone.now():
            raise ValidationError({"status": "El recinto debe estar activo y la fecha debe ser futura."})
    if instance:
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
    data["slug"] = f"{slugify(data['name'])[:170] or 'evento'}-{uuid.uuid4().hex[:8]}"
    return Event.objects.create(**data)


@transaction.atomic
def save_sector(data, instance=None):
    amount = data.pop("price", None)
    if instance:
        sector = lock_inventory([instance.pk])[instance.pk]
        if "event" in data and data["event"].pk != sector.event_id:
            raise ValidationError({"event": "Una localidad no se puede trasladar a otro evento."})
        if "name" in data and data["name"] != sector.name and has_orders([sector.pk]):
            raise Conflict("El nombre de esta localidad forma parte de compras historicas.", "historical_record")
        if data.get("capacity", sector.capacity) < sector.committed:
            raise ValidationError({"capacity": f"Ya hay {sector.committed} entradas comprometidas. No puedes reducir mas la capacidad."})
        for key, value in data.items():
            setattr(sector, key, value)
        sector.save()
    else:
        event = data["event"]
        venue_id = event.venue_id
        Venue.objects.select_for_update().get(pk=venue_id)
        event = Event.objects.select_for_update().get(pk=event.pk)
        if event.venue_id != venue_id:
            raise Conflict("El recinto cambio. Recarga el formulario.", "catalog_changed")
        sector = Sector.objects.create(**data)
    if amount is not None and (not instance or sector.current_amount != amount):
        Price.objects.create(sector=sector, amount=amount)
    return Sector.objects.with_inventory().select_related("event__venue").get(pk=sector.pk)


@transaction.atomic
def delete_resource(instance):
    # La cadena Price -> PurchaseLine bloquea la destruccion del historial.
    if isinstance(instance, Venue):
        Venue.objects.select_for_update().get(pk=instance.pk)
    elif isinstance(instance, Event):
        Venue.objects.select_for_update().get(pk=instance.venue_id)
        Event.objects.select_for_update().get(pk=instance.pk)
    else:
        lock_inventory([instance.pk])
    instance.delete()
