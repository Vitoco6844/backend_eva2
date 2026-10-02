"""Permite que los templates conozcan al usuario del JWT sin usar login de sesion."""
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError


class JWTUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = AnonymousUser()
        request.jwt_expired = False
        raw = request.COOKIES.get(settings.ACCESS_COOKIE)
        if raw:
            try:
                auth = JWTAuthentication()
                request.user = auth.get_user(auth.get_validated_token(raw))
            except (AuthenticationFailed, TokenError):
                request.jwt_expired = True
        response = self.get_response(request)
        if request.user.is_authenticated or request.path.startswith("/api/"):
            response.setdefault("Cache-Control", "private, no-store")
        return response
