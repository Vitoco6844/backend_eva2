"""Estas pruebas usan conexiones reales y bloqueos de PostgreSQL, no SQLite."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connection, connections
from django.test import TransactionTestCase
from catalog.models import Sector
from sales.models import Purchase, Ticket, CartItem
from sales import services
from web.api import Conflict
from .base import fixtures


class ConcurrentSalesTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.buyer, self.other, self.admin, self.venue, self.event, self.sector, self.price = fixtures()

    def order(self, user):
        cart = services.change_item(user, sector_id=self.sector.pk, quantity=1)
        return services.checkout(user, uuid.uuid4(), cart["quote"], cart["version"])[0]

    def simultaneous(self, calls):
        barrier = Barrier(len(calls))
        def worker(call):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                try:
                    return call()
                except Conflict:
                    return "conflict"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            jobs = [pool.submit(worker, call) for call in calls]
            return [job.result(timeout=30) for job in jobs]

    def test_last_ticket_only_one_payment_succeeds(self):
        self.sector.capacity = 1
        self.sector.save()
        a, b = self.order(self.buyer), self.order(self.other)
        results = self.simultaneous([lambda: services.pay(a.pk, self.buyer).status, lambda: services.pay(b.pk, self.other).status])
        self.assertCountEqual(results, ["PAGADO", "conflict"])
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(Sector.objects.with_inventory().get(pk=self.sector.pk).available, 0)

    def test_repeated_payment_produces_one_ticket(self):
        order = self.order(self.buyer)
        self.simultaneous([lambda: services.pay(order.pk, self.buyer), lambda: services.pay(order.pk, self.buyer)])
        self.assertEqual(Ticket.objects.count(), 1)

    def test_repeated_checkout_produces_one_order(self):
        cart = services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)
        key = uuid.uuid4()
        self.simultaneous([lambda: services.checkout(self.buyer, key, cart["quote"], cart["version"]), lambda: services.checkout(self.buyer, key, cart["quote"], cart["version"])])
        self.assertEqual(Purchase.objects.count(), 1)

    def test_concurrent_adds_do_not_lose_quantity(self):
        self.simultaneous([lambda: services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1), lambda: services.change_item(self.buyer, sector_id=self.sector.pk, quantity=1)])
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_repeated_cancel_releases_once(self):
        order = self.order(self.buyer)
        services.pay(order.pk, self.buyer)
        self.simultaneous([lambda: services.cancel(order.pk, self.admin, "A"), lambda: services.cancel(order.pk, self.admin, "B")])
        self.assertEqual(Sector.objects.with_inventory().get(pk=self.sector.pk).available, 5)
        self.assertEqual(order.transitions.filter(new_status="CANCELADO").count(), 1)

    def test_repeated_admission_accepts_once(self):
        order = self.order(self.buyer)
        services.pay(order.pk, self.buyer)
        ticket = Ticket.objects.get()
        results = self.simultaneous([lambda: services.admit(ticket.pk, self.event.pk, self.admin).status, lambda: services.admit(ticket.pk, self.event.pk, self.admin).status])
        self.assertCountEqual(results, ["UTILIZADA", "conflict"])
