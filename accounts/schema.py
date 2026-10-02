"""OpenAPI identifica la cookie de autenticacion sin hacer publico el esquema."""
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "jwtCookie"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": settings.ACCESS_COOKIE,
                "description": "JWT access HttpOnly emitido por login. Escrituras requieren X-CSRFToken."}
