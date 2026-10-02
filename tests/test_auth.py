"""JWT, CSRF, privilegios, privacidad y ciclo de renovacion."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from .base import BaseTest, PASSWORD


class AuthenticationTests(BaseTest):
    def test_login_sets_http_only_jwt_with_role(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessToken(response.cookies["pulso_access"].value)["rol"], "ESPECTADOR")
        self.assertTrue(response.cookies["pulso_access"]["httponly"])
        self.assertTrue(response.cookies["pulso_refresh"]["httponly"])
        self.assertNotIn("password", response.data)

    def test_wrong_login_returns_401(self):
        self.api.get("/ingresar/")
        response = self.api.post("/api/auth/login/", {"username": "lector", "password": "incorrecta"}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 401)

    def test_login_requires_csrf(self):
        response = self.api.post("/api/auth/login/", {"username": "lector", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "csrf_failed")

    def test_registration_is_spectator(self):
        self.api.get("/registrarse/")
        data = {"username": "nuevo", "email": "nuevo@example.test", "first_name": "Nuevo", "last_name": "Usuario", "password": PASSWORD, "password_confirmation": PASSWORD}
        response = self.api.post("/api/auth/registro/", data, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 201, response.content)
        user = get_user_model().objects.get(username="nuevo")
        self.assertEqual(user.role, "ESPECTADOR")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(PASSWORD))

    def test_registration_rejects_privileges(self):
        self.api.get("/registrarse/")
        response = self.api.post("/api/auth/registro/", {"role": "ORGANIZADOR", "is_superuser": True}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 400)

    def test_registration_rejects_weak_or_different_password(self):
        self.api.get("/registrarse/")
        data = {"username": "nuevo", "email": "nuevo@example.test", "first_name": "Nuevo", "last_name": "Usuario", "password": "1234", "password_confirmation": "1234"}
        response = self.api.post("/api/auth/registro/", data, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 400)
        data.update(password=PASSWORD, password_confirmation="diferente")
        self.assertEqual(self.api.post("/api/auth/registro/", data, format="json", HTTP_X_CSRFTOKEN=self.csrf()).status_code, 400)

    def test_case_insensitive_duplicates(self):
        self.api.get("/registrarse/")
        data = {"username": "LECTOR", "email": "LECTOR@EXAMPLE.TEST", "first_name": "Nuevo", "last_name": "Usuario", "password": PASSWORD, "password_confirmation": PASSWORD}
        response = self.api.post("/api/auth/registro/", data, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 400)

    def test_cookie_write_requires_csrf(self):
        self.login()
        response = self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, 403)
        response = self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": 1}, format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 201)

    def test_bearer_accepts_write_without_cookie_csrf(self):
        self.bearer()
        self.assertEqual(self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": 1}, format="json").status_code, 201)

    def test_refresh_rotates_and_rejects_replay(self):
        self.login()
        old = self.api.cookies["pulso_refresh"].value
        response = self.api.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old, self.api.cookies["pulso_refresh"].value)
        self.api.cookies["pulso_refresh"] = old
        self.assertEqual(self.api.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=self.csrf()).status_code, 401)

    def test_logout_revokes_refresh_not_cart(self):
        self.order()
        from sales.services import change_item
        change_item(self.buyer, sector_id=self.sector.pk, quantity=2)
        self.login()
        old = self.api.cookies["pulso_refresh"].value
        self.assertEqual(self.api.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=self.csrf()).status_code, 204)
        self.api.cookies["pulso_refresh"] = old
        self.assertEqual(self.api.post("/api/auth/refresh/", HTTP_X_CSRFTOKEN=self.csrf()).status_code, 401)
        self.login()
        self.assertEqual(self.api.get("/api/carrito/").data["items"][0]["quantity"], 2)

    def test_inactive_user_cannot_use_existing_access(self):
        self.bearer()
        self.buyer.is_active = False
        self.buyer.save()
        self.assertEqual(self.api.get("/api/carrito/").status_code, 401)

    def test_password_change_invalidates_access(self):
        self.bearer()
        self.buyer.set_password("Otra-clave-546378")
        self.buyer.save()
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)

    def test_role_revocation_is_immediate(self):
        self.bearer(self.admin)
        self.admin.is_superuser = False
        self.admin.role = "ESPECTADOR"
        self.admin.save()
        self.assertEqual(self.api.post("/api/recintos/", {}, format="json").status_code, 403)

    def test_expired_access_rejected(self):
        token = self.bearer()
        token.set_exp(lifetime=timedelta(seconds=-1))
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.api.get("/api/carrito/").status_code, 401)

    def test_schema_only_organizer(self):
        self.assertEqual(self.api.get("/api/schema/").status_code, 401)
        self.bearer()
        self.assertEqual(self.api.get("/api/schema/").status_code, 403)
        self.bearer(self.admin)
        self.assertEqual(self.api.get("/api/schema/").status_code, 200)

    def test_docs_and_admin_templates_not_public(self):
        self.assertEqual(self.api.get("/api/docs/").status_code, 401)
        self.assertEqual(self.api.get("/gestion/").status_code, 401)
        self.login()
        self.assertEqual(self.api.get("/api/docs/").status_code, 403)
        self.assertEqual(self.api.get("/gestion/").status_code, 403)

    def test_two_devices_share_cart(self):
        from rest_framework.test import APIClient
        self.bearer()
        self.api.post("/api/carrito/items/", {"sector": self.sector.pk, "quantity": 2}, format="json")
        other_device = APIClient()
        token = self.bearer()
        other_device.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(other_device.get("/api/carrito/").data["items"][0]["quantity"], 2)

    def test_private_api_cannot_be_cached(self):
        self.bearer()
        self.assertIn("no-store", self.api.get("/api/carrito/")["Cache-Control"])
        self.assertIn("no-store", self.api.get("/api/compras/")["Cache-Control"])
