"""Stock, atomicidad, precios historicos, estados y entradas por unidad."""
import uuid
from unittest.mock import patch
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from catalog.models import Event, Sector, Price
from catalog.services import save_sector
from sales.models import Cart, CartItem, Purchase, PurchaseLine, Ticket
from sales import services
from web.api import Conflict
from .base import BaseTest


class SalesTests(BaseTest):
    def test_anonymous_cannot_add(self):
        self.assertEqual(self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": 1}, format="json").status_code, 401)
        self.assertFalse(CartItem.objects.exists())

    def test_organizer_cannot_buy_as_client(self):
        self.bearer(self.admin)
        self.assertEqual(self.api.get("/api/carrito/").status_code, 403)

    def test_cart_does_not_consume_stock(self):
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=3)
        self.assertEqual(self.available(), 5)

    def test_cart_adds_to_same_row(self):
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=2)
        self.assertEqual(CartItem.objects.get().quantity, 3)

    def test_quantity_validation_and_forged_fields(self):
        self.bearer()
        for quantity in [0, -1, 101, 1.5, "mal"]:
            with self.subTest(quantity=quantity):
                self.assertEqual(self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": quantity}, format="json").status_code, 400)
        response = self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": 1, "price": 1, "user": self.other.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cart_ownership(self):
        data = services.change_item(self.other, sector_id=self.sector.pk, quantity=1)
        item_id = data["items"][0]["id"]
        self.bearer()
        self.assertEqual(self.api.patch(f"/api/carrito/items/{item_id}/", {"quantity": 2}, format="json").status_code, 404)
        self.assertEqual(self.api.delete(f"/api/carrito/items/{item_id}/").status_code, 404)

    def test_clear_cart_preserves_one_to_one(self):
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        services.clear_cart(self.buyer)
        self.assertEqual(Cart.objects.filter(user=self.buyer).count(), 1)
        self.assertFalse(CartItem.objects.exists())

    def test_empty_checkout_rejected(self):
        with self.assertRaises(ValidationError):
            services.checkout(self.buyer, uuid.uuid4(), "", 0)

    def test_checkout_pending_clears_cart_without_stock_decrement(self):
        order = self.order(quantity=2)
        self.assertEqual(order.status, "PENDIENTE")
        self.assertEqual(order.total, 20000)
        self.assertFalse(CartItem.objects.exists())
        self.assertEqual(self.available(), 5)
        self.assertFalse(Ticket.objects.exists())

    def test_price_change_requires_new_quote(self):
        cart = services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        save_sector({"price": 12000}, self.sector)
        with self.assertRaises(Conflict):
            services.checkout(self.buyer, uuid.uuid4(), cart["quote"], cart["version"])
        self.assertFalse(Purchase.objects.exists())
        self.assertTrue(CartItem.objects.exists())

    def test_quote_cannot_be_tampered_or_transferred(self):
        cart = services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        other = services.change_item(self.other, sector_id=self.sector.pk, quantity=1)
        for quote in [cart["quote"] + "x", other["quote"]]:
            with self.assertRaises(Conflict):
                services.checkout(self.buyer, uuid.uuid4(), quote, cart["version"])

    def test_cart_version_detects_another_tab(self):
        cart = services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        with self.assertRaises(Conflict):
            services.checkout(self.buyer, uuid.uuid4(), cart["quote"], cart["version"])

    def test_checkout_idempotency(self):
        cart = services.change_item(self.buyer, sector_id=self.sector.pk, quantity=2)
        key = uuid.uuid4()
        one, created = services.checkout(self.buyer, key, cart["quote"], cart["version"])
        two, repeated = services.checkout(self.buyer, key, cart["quote"], cart["version"])
        self.assertEqual(one.pk, two.pk)
        self.assertTrue(created)
        self.assertFalse(repeated)
        self.assertEqual(Purchase.objects.count(), 1)

    def test_payment_decrements_and_issues_unique_units_once(self):
        order = self.order(quantity=3)
        services.pay(order.pk, self.buyer)
        services.pay(order.pk, self.buyer)
        self.assertEqual(self.available(), 2)
        self.assertEqual(Ticket.objects.count(), 3)
        self.assertEqual(len(set(Ticket.objects.values_list("id", flat=True))), 3)

    def test_checkout_key_cannot_identify_another_payload(self):
        cart = services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        key = uuid.uuid4()
        services.checkout(self.buyer, key, cart["quote"], cart["version"])
        with self.assertRaises(Conflict):
            services.checkout(self.buyer, key, cart["quote"], cart["version"] + 1)

    def test_pending_preserves_accepted_price(self):
        order = self.order(quantity=2)
        save_sector({"price": 30000}, self.sector)
        services.pay(order.pk, self.buyer)
        self.assertEqual(Purchase.objects.get(pk=order.pk).total, 20000)
        self.assertEqual(Price.objects.filter(sector=self.sector).count(), 2)

    def test_rejected_payment_leaves_state_and_stock(self):
        order = self.order()
        with self.assertRaises(Conflict):
            services.pay(order.pk, self.buyer, approved=False)
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDIENTE")
        self.assertFalse(Ticket.objects.exists())
        self.assertEqual(self.available(), 5)

    def test_insufficient_stock_rejects_whole_mixed_purchase(self):
        second = Sector.objects.create(event=self.event, name="Preferencial", capacity=1)
        Price.objects.create(sector=second, amount=20000)
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=2)
        order = self.order(sector=second)
        competing = self.order(user=self.other, sector=second)
        services.pay(competing.pk, self.other)
        with self.assertRaises(Conflict):
            services.pay(order.pk, self.buyer)
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDIENTE")
        self.assertEqual(self.available(), 5)
        self.assertFalse(Ticket.objects.filter(line__purchase=order).exists())

    def test_ticket_generation_failure_rolls_back_payment(self):
        order = self.order(quantity=2)
        with patch("sales.services.Ticket.objects.bulk_create", side_effect=RuntimeError("Simulated failure")):
            with self.assertRaises(RuntimeError):
                services.pay(order.pk, self.buyer)
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDIENTE")
        self.assertEqual(self.available(), 5)

    def test_cancel_paid_restores_once_and_invalidates_tickets(self):
        order = self.order(quantity=2)
        services.pay(order.pk, self.buyer)
        services.cancel(order.pk, self.admin, "Prueba")
        services.cancel(order.pk, self.admin, "Repetido")
        self.assertEqual(self.available(), 5)
        self.assertTrue(all(ticket.status == "ANULADA" for ticket in Ticket.objects.select_related("line__purchase")))
        self.assertEqual(order.transitions.filter(new_status="CANCELADO").count(), 1)

    def test_cancel_pending_does_not_add_capacity(self):
        order = self.order()
        services.cancel(order.pk, self.admin, "Prueba")
        self.assertEqual(self.available(), 5)

    def test_cancelled_cannot_be_paid(self):
        order = self.order()
        services.cancel(order.pk, self.admin, "Prueba")
        with self.assertRaises(Conflict):
            services.pay(order.pk, self.buyer)

    def test_ticket_admission_once_and_all_delivered(self):
        order = self.order(quantity=2)
        services.pay(order.pk, self.buyer)
        tickets = list(Ticket.objects.all())
        services.admit(tickets[0].pk, self.event.pk, self.admin)
        order.refresh_from_db()
        self.assertEqual(order.status, "PAGADO")
        with self.assertRaises(Conflict):
            services.admit(tickets[0].pk, self.event.pk, self.admin)
        services.admit(tickets[1].pk, self.event.pk, self.admin)
        order.refresh_from_db()
        self.assertEqual(order.status, "ENTREGADO")
        self.assertEqual(self.available(), 3)

    def test_ticket_wrong_event_rejected(self):
        order = self.order()
        services.pay(order.pk, self.buyer)
        with self.assertRaises(ValidationError):
            services.admit(Ticket.objects.get().pk, 9999, self.admin)
        self.assertIsNone(Ticket.objects.get().used_at)

    def test_deliver_and_cancel_delivered(self):
        order = self.order()
        services.pay(order.pk, self.buyer)
        services.deliver(order.pk, self.admin, "Ingreso")
        services.deliver(order.pk, self.admin, "Repetido")
        self.assertIsNotNone(Ticket.objects.get().used_at)
        services.cancel(order.pk, self.admin, "Correccion administrativa")
        self.assertEqual(self.available(), 5)
        self.assertEqual(Ticket.objects.get().status, "ANULADA")

    def test_deliver_pending_rejected(self):
        with self.assertRaises(Conflict):
            services.deliver(self.order().pk, self.admin, "Prueba")

    def test_purchase_and_ticket_ownership(self):
        order = self.order(user=self.other)
        services.pay(order.pk, self.other)
        ticket = Ticket.objects.get()
        self.bearer()
        self.assertEqual(self.api.get(f"/api/compras/{order.pk}/").status_code, 404)
        self.assertEqual(self.api.post(f"/api/compras/{order.pk}/pagar/", {"result": "approved"}, format="json").status_code, 404)
        self.assertEqual(self.api.get("/api/mis-entradas/").data["count"], 0)
        self.login()
        self.api.credentials()
        self.assertEqual(self.api.get(f"/entradas/{ticket.pk}/").status_code, 404)
        self.assertEqual(self.api.get(f"/entradas/{ticket.pk}/qr/").status_code, 404)

    def test_only_admin_changes_status(self):
        order = self.order()
        self.bearer()
        self.assertEqual(self.api.patch(f"/api/compras/{order.pk}/estado/", {"status": "PAGADO"}, format="json").status_code, 403)
        self.bearer(self.admin)
        self.assertEqual(self.api.patch(f"/api/compras/{order.pk}/estado/", {"status": "PAGADO"}, format="json").status_code, 200)
        self.assertEqual(self.api.patch(f"/api/compras/{order.pk}/estado/", {"status": "ENTREGADO"}, format="json").status_code, 200)
        self.assertEqual(self.api.patch(f"/api/compras/{order.pk}/estado/", {"status": "CANCELADO", "reason": "Prueba"}, format="json").status_code, 200)

    def test_database_rejects_invalid_quantity(self):
        cart = services.cart_for(self.buyer)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, sector=self.sector, quantity=0)

    def test_equivalent_rubric_endpoints(self):
        self.bearer()
        response = self.api.post("/api/carro-tickets/", {"sector": self.sector.pk, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, 201)
        cart = self.api.get("/api/carro-tickets/").data
        order = self.api.post("/api/checkout/", {"checkout_key": str(uuid.uuid4()), "quote": cart["quote"], "version": cart["version"]}, format="json")
        self.assertEqual(order.status_code, 201)
        self.assertEqual(self.api.post("/api/compras/pagar/", {"purchase": order.data["id"], "result": "approved"}, format="json").status_code, 200)
        self.assertEqual(self.api.get("/api/mis-entradas/").data["count"], 1)
        self.assertEqual(self.api.delete("/api/carro-tickets/").status_code, 200)

    def test_two_events_in_same_purchase(self):
        event = Event.objects.create(name="Segundo", artist="Otra banda", slug="segundo", description="Prueba", starts_at=self.event.starts_at, venue=self.venue, status="PUBLICADO")
        sector = Sector.objects.create(event=event, name="General", capacity=5)
        Price.objects.create(sector=sector, amount=15000)
        services.change_item(self.buyer, sector_id=self.sector.pk, quantity=2)
        order = self.order(sector=sector)
        services.pay(order.pk, self.buyer)
        self.assertEqual(order.total, 35000)
        self.assertEqual(order.lines.count(), 2)
        self.assertEqual(Ticket.objects.count(), 3)
