"""Datos aislados para pruebas; nunca usan las cuentas ni compras del alumno."""
import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from catalog.models import Venue, Event, Sector, Price
from sales import services


PASSWORD = "Prueba-segura-48291"


def fixtures():
    User = get_user_model()
    buyer = User.objects.create_user("lector", "lector@example.test", PASSWORD, first_name="Lector", last_name="Prueba")
    other = User.objects.create_user("otro", "otro@example.test", PASSWORD)
    admin = User.objects.create_superuser("organizador", "admin@example.test", PASSWORD)
    venue = Venue.objects.create(name="Recinto prueba", city="Santiago", address="Calle 123")
    event = Event.objects.create(name="Evento prueba", artist="Banda prueba", slug="evento-prueba", description="Concierto sintetico", starts_at=timezone.now() + timedelta(days=10), venue=venue, status="PUBLICADO")
    sector = Sector.objects.create(name="General", event=event, capacity=5)
    price = Price.objects.create(sector=sector, amount=10000)
    return buyer, other, admin, venue, event, sector, price


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.buyer, cls.other, cls.admin, cls.venue, cls.event, cls.sector, cls.price = fixtures()

    def setUp(self):
        cache.clear()
        self.api = APIClient(enforce_csrf_checks=True)

    def bearer(self, user=None):
        token = RefreshToken.for_user(user or self.buyer).access_token
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def login(self, user=None):
        user = user or self.buyer
        self.api.get("/ingresar/")
        return self.api.post("/api/auth/login/", {"username": user.username, "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=self.csrf())

    def csrf(self):
        return self.api.cookies["csrftoken"].value

    def order(self, user=None, quantity=1, sector=None):
        user, sector = user or self.buyer, sector or self.sector
        cart = services.change_item(user, sector_id=sector.pk, quantity=quantity)
        return services.checkout(user, uuid.uuid4(), cart["quote"], cart["version"])[0]

    def available(self, sector=None):
        return Sector.objects.with_inventory().get(pk=(sector or self.sector).pk).available
