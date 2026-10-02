"""CRUD, relaciones 3FN, restricciones historicas y filtros SQL."""
from django.core.exceptions import ValidationError as ModelValidationError
from django.test import override_settings
from django.utils import timezone
from catalog.models import Event, Sector, Price
from catalog.services import save_sector, save_event, save_venue
from sales import services
from sales.models import Purchase, PurchaseLine, Ticket
from rest_framework.exceptions import ValidationError
from web.api import Conflict
from .base import BaseTest


class CatalogTests(BaseTest):
    def test_public_catalog_json_not_browsable_drf(self):
        response = self.api.get("/api/eventos/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 406)
        response = self.api.get("/api/eventos/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertIn(".png", response.data["results"][0]["cover_url"])

    def test_public_cannot_read_draft(self):
        self.event.status = "BORRADOR"
        self.event.save()
        self.assertEqual(self.api.get("/api/eventos/").data["count"], 0)
        self.assertEqual(self.api.get(f"/api/eventos/{self.event.pk}/").status_code, 404)
        self.assertEqual(self.api.get(f"/eventos/{self.event.pk}/").status_code, 404)
        self.bearer(self.admin)
        self.assertEqual(self.api.get(f"/api/eventos/{self.event.pk}/").status_code, 200)

    def test_public_cannot_write(self):
        for path in ["recintos", "eventos", "sectores"]:
            self.assertEqual(self.api.post(f"/api/{path}/", {}, format="json").status_code, 401)
        self.bearer()
        self.assertEqual(self.api.delete(f"/api/eventos/{self.event.pk}/").status_code, 403)

    def test_organizer_crud_venue(self):
        self.bearer(self.admin)
        response = self.api.post("/api/recintos/", {"name": "Nuevo", "city": "Temuco", "address": "Calle 10", "active": True}, format="json")
        self.assertEqual(response.status_code, 201)
        pk = response.data["id"]
        self.assertEqual(self.api.patch(f"/api/recintos/{pk}/", {"name": "Editado"}, format="json").status_code, 200)
        self.assertEqual(self.api.delete(f"/api/recintos/{pk}/").status_code, 204)

    def test_organizer_event_draft_sector_publish_delete(self):
        self.bearer(self.admin)
        data = {"name": "Nuevo concierto", "artist": "Banda", "venue": self.venue.pk, "starts_at": self.event.starts_at.isoformat(), "description": "Prueba", "status": "BORRADOR"}
        response = self.api.post("/api/eventos/", data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(self.api.patch(f"/api/eventos/{pk}/", {"status": "PUBLICADO"}, format="json").status_code, 400)
        response = self.api.post("/api/sectores/", {"event": pk, "name": "Cancha", "capacity": 20, "price": 20000}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.api.patch(f"/api/eventos/{pk}/", {"status": "PUBLICADO"}, format="json").status_code, 200)
        self.assertEqual(self.api.delete(f"/api/eventos/{pk}/").status_code, 204)

    def test_bulk_and_csv_input_not_supported(self):
        self.bearer(self.admin)
        self.assertEqual(self.api.post("/api/recintos/", [{"name": "X"}], format="json").status_code, 400)
        self.assertEqual(self.api.post("/api/eventos/importar/", {}, format="json").status_code, 404)
        self.assertEqual(self.api.post("/api/recintos/", "name,city\nX,Y", content_type="text/csv").status_code, 415)

    def test_invalid_prices_and_capacities(self):
        self.bearer(self.admin)
        for payload in [{"price": 0}, {"capacity": -1}, {"price": 1.5}, {"capacity": 1000001}]:
            self.assertEqual(self.api.patch(f"/api/sectores/{self.sector.pk}/", payload, format="json").status_code, 400)

    def test_historical_references_protected(self):
        self.order()
        self.bearer(self.admin)
        for kind, pk in [("eventos", self.event.pk), ("sectores", self.sector.pk), ("recintos", self.venue.pk)]:
            self.assertEqual(self.api.delete(f"/api/{kind}/{pk}/").status_code, 409)
        with self.assertRaises(Conflict):
            save_event({"name": "Historia alterada"}, self.event)
        with self.assertRaises(Conflict):
            save_venue({"address": "Direccion alterada"}, self.venue)
        with self.assertRaises(Conflict):
            save_sector({"name": "Nombre alterado"}, self.sector)

    def test_capacity_cannot_drop_below_paid(self):
        order = self.order(quantity=3)
        services.pay(order.pk, self.buyer)
        with self.assertRaises(ValidationError):
            save_sector({"capacity": 2}, self.sector)
        save_sector({"capacity": 3}, self.sector)
        self.assertEqual(self.available(), 0)

    def test_archive_keeps_tickets_and_cannot_be_bought(self):
        order = self.order()
        services.pay(order.pk, self.buyer)
        save_event({"status": "ARCHIVADO"}, self.event)
        self.assertEqual(Ticket.objects.count(), 1)
        with self.assertRaises(Conflict):
            services.change_item(self.other, sector_id=self.sector.pk, quantity=1)

    def test_price_rows_immutable(self):
        self.price.amount = 1
        with self.assertRaises(ModelValidationError):
            self.price.save()

    def test_3nf_no_stored_totals_or_duplicated_relations(self):
        self.assertNotIn("total", {f.name for f in Purchase._meta.fields})
        fields = {f.name for f in PurchaseLine._meta.fields}
        self.assertEqual(fields, {"id", "purchase", "price", "quantity"})
        self.assertNotIn("stock", {f.name for f in Sector._meta.fields})
        self.assertNotIn("user", {f.name for f in Ticket._meta.fields})

    def test_filters_use_actual_data(self):
        self.assertEqual(self.api.get("/api/eventos/?ciudad=Santiago&precio_min=9000&precio_max=11000").data["count"], 1)
        self.assertEqual(self.api.get("/api/eventos/?ciudad=Osorno").data["count"], 0)
        self.assertEqual(self.api.get("/api/eventos/?q=Banda").data["count"], 1)
        self.assertEqual(self.api.get("/api/eventos/?fecha_desde=mal").status_code, 400)
        self.assertEqual(self.api.get("/api/eventos/?precio_min=50&precio_max=10").status_code, 400)

    def test_price_range_must_match_same_sector(self):
        sector = Sector.objects.create(event=self.event, name="VIP", capacity=5)
        Price.objects.create(sector=sector, amount=50000)
        self.assertEqual(self.api.get("/api/eventos/?precio_min=20000&precio_max=30000").data["count"], 0)

    def test_availability_filter_after_payment(self):
        services.pay(self.order(quantity=5).pk, self.buyer)
        self.assertEqual(self.api.get("/api/eventos/?disponibles=true").data["count"], 0)
        self.assertEqual(self.api.get("/api/eventos/?disponibles=false").data["count"], 1)

    @override_settings(DEBUG=False)
    def test_friendly_404_and_valid_status(self):
        for path in ["/ruta-inexistente/", "/eventos/99999/", "/admin/"]:
            response = self.api.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertContains(response, "Volver a eventos", status_code=404)
            self.assertNotContains(response, "Django administration", status_code=404)
        response = self.api.get("/api/inexistente/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "404")

    def test_footer_and_navigation_html(self):
        response = self.api.get("/")
        self.assertContains(response, "Vicente Mateo")
        self.assertContains(response, "AP-N4-C1")
        self.assertContains(response, "2026")
        self.assertContains(response, 'href="/ingresar/"')

    def test_uploaded_non_image_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.bearer(self.admin)
        response = self.api.patch(f"/api/eventos/{self.event.pk}/", {"image": SimpleUploadedFile("fake.png", b"<script>alert(1)</script>", content_type="image/png")}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_upload_extension_comes_from_verified_format(self):
        from io import BytesIO
        from tempfile import TemporaryDirectory
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        content = BytesIO()
        Image.new("RGB", (4, 4), "white").save(content, format="PNG")
        self.bearer(self.admin)
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            response = self.api.patch(f"/api/eventos/{self.event.pk}/", {"image": SimpleUploadedFile("archivo.html", content.getvalue(), content_type="text/html")}, format="multipart")
            self.assertEqual(response.status_code, 400)
            response = self.api.patch(f"/api/eventos/{self.event.pk}/", {"image": SimpleUploadedFile("archivo.jpg", content.getvalue(), content_type="image/jpeg")}, format="multipart")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data["image"].endswith(".png"))
            self.assertNotIn("archivo.html", response.data["image"])
