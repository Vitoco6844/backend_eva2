"""Reglas de venta: operaciones atomicas y disponibilidad calculada, sin reservas."""
import hashlib
import json

from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from catalog.models import Sector
from catalog.services import assert_sellable, lock_inventory
from web.api import Conflict
from .models import Cart, CartItem, Purchase, PurchaseLine, Ticket, PurchaseTransition


def cart_for(user, locked=False):
    cart, _ = Cart.objects.get_or_create(user=user)
    return Cart.objects.select_for_update().get(pk=cart.pk) if locked else cart


def cart_rows(cart):
    items = list(cart.items.select_related("sector__event__venue"))
    sectors = {s.pk: s for s in Sector.objects.with_inventory().filter(pk__in=[i.sector_id for i in items]).select_related("event__venue")}
    rows = []
    for item in items:
        sector = sectors[item.sector_id]
        rows.append({"id": item.pk, "sector": sector.pk, "event": sector.event_id,
                     "event_name": sector.event.name, "sector_name": sector.name,
                     "starts_at": sector.event.starts_at, "venue": sector.event.venue.name,
                     "quantity": item.quantity, "unit_price": sector.current_amount or 0,
                     "price_id": sector.current_price_id, "available": sector.available,
                     "sellable": bool(sector.active and sector.event.is_sellable and sector.current_price_id),
                     "subtotal": item.quantity * (sector.current_amount or 0)})
    return rows


def quote_digest(rows):
    contents = sorted((r["sector"], r["quantity"], r["price_id"]) for r in rows)
    return hashlib.sha256(json.dumps(contents).encode()).hexdigest()


def cart_data(user):
    cart = cart_for(user)
    rows = cart_rows(cart)
    # La firma exige aceptar nuevamente el resumen cuando cambian las tarifas.
    quote = signing.dumps({"user": user.pk, "version": cart.version, "digest": quote_digest(rows)}, salt="checkout")
    return {"version": cart.version, "items": rows, "total": sum(r["subtotal"] for r in rows), "quote": quote}


@transaction.atomic
def change_item(user, sector_id=None, quantity=None, item_id=None, remove=False):
    cart = cart_for(user, locked=True)
    item = None
    if item_id is not None:
        item = cart.items.filter(pk=item_id).first()
        if not item:
            raise NotFound("Ese elemento no pertenece a tu carrito.")
        sector_id = item.sector_id
    if remove:
        item.delete()
    else:
        sector = lock_inventory([sector_id])[sector_id]
        assert_sellable(sector)
        if item is None:
            item = cart.items.filter(sector_id=sector_id).first()
            quantity += item.quantity if item else 0
        if quantity > 100 or quantity > sector.available:
            raise Conflict(f"Solo quedan {sector.available} cupos; maximo 100 por localidad.", "insufficient_stock")
        if item:
            item.quantity = quantity
            item.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(cart=cart, sector=sector, quantity=quantity)
    cart.version += 1
    cart.save(update_fields=["version", "updated_at"])
    return cart_data(user)


@transaction.atomic
def clear_cart(user):
    cart = cart_for(user, locked=True)
    cart.items.all().delete()
    cart.version += 1
    cart.save(update_fields=["version", "updated_at"])
    return cart_data(user)


@transaction.atomic
def checkout(user, checkout_key, quote, version):
    cart = cart_for(user, locked=True)
    digest = hashlib.sha256(f"{version}:{quote}".encode()).hexdigest()
    previous = Purchase.objects.filter(user=user, checkout_key=checkout_key).first()
    if previous:
        if previous.checkout_digest != digest:
            raise Conflict("Esta clave de confirmacion ya fue usada con otro resumen.", "idempotency_conflict")
        return previous, False
    items = list(cart.items.all())
    if not items:
        raise ValidationError("Tu carrito esta vacio.")
    inventory = lock_inventory([item.sector_id for item in items])
    try:
        accepted = signing.loads(quote, salt="checkout", max_age=1800)
    except signing.BadSignature as exc:
        raise Conflict("El resumen vencio. Actualiza el carrito.", "quote_expired") from exc
    rows = cart_rows(cart)
    if accepted != {"user": user.pk, "version": cart.version, "digest": quote_digest(rows)} or version != cart.version:
        raise Conflict("El carrito o sus precios cambiaron. Revisa el nuevo resumen.", "quote_changed")
    for item in items:
        sector = inventory[item.sector_id]
        assert_sellable(sector)
        if item.quantity > sector.available:
            raise Conflict(f"No quedan suficientes entradas para {sector.name}.", "insufficient_stock")
    purchase = Purchase.objects.create(user=user, checkout_key=checkout_key, checkout_digest=digest)
    PurchaseLine.objects.bulk_create([PurchaseLine(purchase=purchase, price_id=inventory[i.sector_id].current_price_id, quantity=i.quantity) for i in items])
    PurchaseTransition.objects.create(purchase=purchase, actor=user, previous_status="", new_status=purchase.status, reason="Confirmacion de carrito")
    cart.items.all().delete()
    cart.version += 1
    cart.save(update_fields=["version", "updated_at"])
    return purchase, True


def record_status(purchase, actor, target, reason=""):
    old = purchase.status
    purchase.status = target
    purchase.save(update_fields=["status", "paid_at", "cancelled_at"])
    PurchaseTransition.objects.create(purchase=purchase, actor=actor, previous_status=old, new_status=target, reason=reason)


@transaction.atomic
def pay(purchase_id, actor, approved=True):
    purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
    if purchase.status in [Purchase.Status.PAID, Purchase.Status.DELIVERED]:
        return purchase
    if purchase.status != Purchase.Status.PENDING:
        raise Conflict("Una compra cancelada no puede pagarse.", "invalid_transition")
    if not approved:
        raise Conflict("Pago de demostracion rechazado. La compra sigue pendiente.", "payment_declined")
    lines = list(purchase.lines.select_related("price"))
    inventory = lock_inventory([line.price.sector_id for line in lines])
    for line in lines:
        sector = inventory[line.price.sector_id]
        assert_sellable(sector)
        if line.quantity > sector.available:
            raise Conflict(f"Se agotaron los cupos de {sector.name}. No se cobro ni se emitieron entradas.", "insufficient_stock")
    # El cambio de estado consume cupos; los UUID se crean en la misma transaccion.
    purchase.paid_at = timezone.now()
    record_status(purchase, actor, Purchase.Status.PAID, "Pago de demostracion aprobado; sin cargo real")
    Ticket.objects.bulk_create([Ticket(line=line, ordinal=n) for line in lines for n in range(1, line.quantity + 1)])
    return purchase


@transaction.atomic
def cancel(purchase_id, actor, reason):
    purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
    if purchase.status == Purchase.Status.CANCELLED:
        return purchase
    sector_ids = purchase.lines.values_list("price__sector_id", flat=True)
    lock_inventory(sector_ids)
    purchase.cancelled_at = timezone.now()
    record_status(purchase, actor, Purchase.Status.CANCELLED, reason)
    return purchase


@transaction.atomic
def admit(ticket_id, event_id, actor):
    stub = Ticket.objects.filter(pk=ticket_id).values("line__purchase_id").first()
    if not stub:
        raise NotFound("Entrada no encontrada.")
    purchase = Purchase.objects.select_for_update().get(pk=stub["line__purchase_id"])
    ticket = Ticket.objects.select_for_update().select_related("line__price__sector").get(pk=ticket_id)
    if ticket.line.price.sector.event_id != event_id:
        raise ValidationError({"event": "La entrada no corresponde a este evento."})
    if purchase.status != Purchase.Status.PAID or ticket.used_at:
        raise Conflict("La entrada esta anulada, ya se utilizo o no esta pagada.", "invalid_ticket")
    ticket.used_at = timezone.now()
    ticket.save(update_fields=["used_at"])
    if not Ticket.objects.filter(line__purchase=purchase, used_at__isnull=True).exists():
        record_status(purchase, actor, Purchase.Status.DELIVERED, "Todas las entradas fueron utilizadas")
    return ticket


@transaction.atomic
def deliver(purchase_id, actor, reason):
    purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
    if purchase.status == Purchase.Status.DELIVERED:
        return purchase
    if purchase.status != Purchase.Status.PAID:
        raise Conflict("Solo una compra pagada puede registrar entrega.", "invalid_transition")
    # Accion administrativa explicita: registra el ingreso de todas las unidades restantes.
    Ticket.objects.filter(line__purchase=purchase, used_at__isnull=True).update(used_at=timezone.now())
    record_status(purchase, actor, Purchase.Status.DELIVERED, reason or "Ingreso completo confirmado por organizador")
    return purchase


def change_status(purchase, actor, target, reason):
    if target == Purchase.Status.CANCELLED:
        if not reason.strip():
            raise ValidationError({"reason": "Indica el motivo de cancelacion."})
        return cancel(purchase.pk, actor, reason)
    if target == Purchase.Status.PAID:
        return pay(purchase.pk, actor)
    if target == Purchase.Status.DELIVERED:
        return deliver(purchase.pk, actor, reason)
    raise Conflict("No se puede retroceder una compra.", "invalid_transition")
