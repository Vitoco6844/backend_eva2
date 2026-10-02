"""JWT en cookie HttpOnly; las escrituras por cookie siempre verifican CSRF."""
from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


def enforce_csrf(request):
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied("No pudimos validar la solicitud. Recarga la pagina e intentalo nuevamente.")


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Un Bearer explicito tiene precedencia; nunca mezclar dos identidades.
        if self.get_header(request) is not None:
            return super().authenticate(request)
        raw = request.COOKIES.get(settings.ACCESS_COOKIE)
        if not raw:
            return None
        token = self.get_validated_token(raw)
        user = self.get_user(token)
        enforce_csrf(request)
        return user, token
