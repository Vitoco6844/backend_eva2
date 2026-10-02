"""Entidades en 3FN: una tarifa historica pertenece a un unico sector."""
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import OuterRef, Subquery, Sum, IntegerField, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone


class Venue(models.Model):
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=220)
    city = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [models.UniqueConstraint(fields=["name", "city"], name="venue_name_city_unique")]

    def __str__(self):
        return f"{self.name} / {self.city}"


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "BORRADOR", "Borrador"
        PUBLISHED = "PUBLICADO", "Publicado"
        ARCHIVED = "ARCHIVADO", "Archivado"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=200, unique=True)
    artist = models.CharField(max_length=160)
    description = models.TextField(max_length=5000)
    starts_at = models.DateTimeField(db_index=True)
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT, db_index=True)
    image = models.ImageField(upload_to="events/%Y/%m/", blank=True)
    artwork = models.CharField(max_length=20, default="live", choices=[("live", "En vivo"), ("electronic", "Electronica"), ("acoustic", "Acustico")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [models.CheckConstraint(condition=models.Q(status__in=["BORRADOR", "PUBLICADO", "ARCHIVADO"]), name="event_status_valid")]

    @property
    def is_sellable(self):
        return self.status == self.Status.PUBLISHED and self.starts_at > timezone.now() and self.venue.active

    def __str__(self):
        return self.name


class SectorQuerySet(models.QuerySet):
    def with_inventory(self):
        # Stock derivado: capacidad menos unidades pagadas, nunca otra copia editable.
        from sales.models import PurchaseLine

        committed = PurchaseLine.objects.filter(
            price__sector_id=OuterRef("pk"), purchase__status__in=["PAGADO", "ENTREGADO"],
        ).order_by().values("price__sector_id").annotate(n=Sum("quantity")).values("n")
        latest_price = Price.objects.filter(sector_id=OuterRef("pk")).order_by("-pk")
        return self.annotate(
            committed=Coalesce(Subquery(committed, output_field=IntegerField()), Value(0)),
            available=F("capacity") - F("committed"),
            current_amount=Subquery(latest_price.values("amount")[:1]),
            current_price_id=Subquery(latest_price.values("pk")[:1]),
        )


class Sector(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sectors")
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True)
    objects = SectorQuerySet.as_manager()

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["event", "name"], name="sector_event_name_unique"),
            models.CheckConstraint(condition=models.Q(capacity__gte=0), name="sector_capacity_nonnegative"),
        ]

    def __str__(self):
        return f"{self.event.name}: {self.name}"


class Price(models.Model):
    """Cada cambio crea una tarifa; una compra referencia la tarifa que acepto."""
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="prices")
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="price_positive")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            from django.core.exceptions import ValidationError
            raise ValidationError("Las tarifas son inmutables. Crea una nueva tarifa.")
        return super().save(*args, **kwargs)
