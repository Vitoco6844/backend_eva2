"""Modelo transaccional 3FN: sin duplicar sector, precio, total o comprador."""
import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    sector = models.ForeignKey("catalog.Sector", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "sector"], name="cart_sector_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cart_quantity_positive"),
        ]


class Purchase(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDIENTE", "Pendiente"
        PAID = "PAGADO", "Pagado"
        DELIVERED = "ENTREGADO", "Entregado"
        CANCELLED = "CANCELADO", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases")
    status = models.CharField(max_length=12, choices=Status, default=Status.PENDING, db_index=True)
    checkout_key = models.UUIDField()
    checkout_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "checkout_key"], name="purchase_checkout_unique"),
            models.CheckConstraint(condition=models.Q(status__in=["PENDIENTE", "PAGADO", "ENTREGADO", "CANCELADO"]), name="purchase_status_valid"),
        ]

    @property
    def total(self):
        return sum(line.quantity * line.price.amount for line in self.lines.all())


class PurchaseLine(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="lines")
    price = models.ForeignKey("catalog.Price", on_delete=models.PROTECT, related_name="purchase_lines")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["purchase", "price"], name="purchase_price_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="purchase_quantity_positive"),
        ]

    @property
    def subtotal(self):
        return self.quantity * self.price.amount


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    line = models.ForeignKey(PurchaseLine, on_delete=models.PROTECT, related_name="tickets")
    ordinal = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["issued_at", "ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["line", "ordinal"], name="ticket_line_ordinal_unique"),
            models.CheckConstraint(condition=models.Q(ordinal__gt=0), name="ticket_ordinal_positive"),
        ]

    @property
    def status(self):
        if self.line.purchase.status == Purchase.Status.CANCELLED:
            return "ANULADA"
        return "UTILIZADA" if self.used_at else "VIGENTE"


class PurchaseTransition(models.Model):
    """Bitacora de acciones; no sustituye a la compra ni duplica su contenido."""
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="transitions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    previous_status = models.CharField(max_length=12, blank=True)
    new_status = models.CharField(max_length=12)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
