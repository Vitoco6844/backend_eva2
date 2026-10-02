"""Emision, renovacion y revocacion de tokens; el carrito nunca se borra al salir."""
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.middleware.csrf import rotate_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from .serializers import LoginSerializer, RegistrationSerializer, ProfileSerializer


def issue_tokens(user, response):
    refresh = RefreshToken.for_user(user)
    refresh["rol"] = user.effective_role
    access = refresh.access_token
    shared = {"httponly": True, "secure": settings.COOKIE_SECURE, "samesite": "Lax"}
    response.set_cookie(settings.ACCESS_COOKIE, str(access), max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()), path="/", **shared)
    response.set_cookie(settings.REFRESH_COOKIE, str(refresh), max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()), path="/api/auth/", **shared)
    response["Cache-Control"] = "no-store"
    return response


@method_decorator(csrf_protect, name="dispatch")
class PublicAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def get_authenticate_header(self, request):
        return "Bearer"


class LoginView(PublicAuthView):
    @extend_schema(request=LoginSerializer, responses=ProfileSerializer, tags=["Cuenta"])
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if not user:
            raise AuthenticationFailed("Usuario o contrasena incorrectos.")
        rotate_token(request)
        return issue_tokens(user, Response(ProfileSerializer(user).data))


class RegisterView(PublicAuthView):
    @extend_schema(request=RegistrationSerializer, responses={201: ProfileSerializer}, tags=["Cuenta"])
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        rotate_token(request)
        return issue_tokens(user, Response(ProfileSerializer(user).data, status=status.HTTP_201_CREATED))


class RefreshView(PublicAuthView):
    @extend_schema(request=None, responses=ProfileSerializer, tags=["Cuenta"])
    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE, "")
        try:
            # Bloquear el token pendiente impide que dos renovaciones reutilicen el mismo refresh.
            token = RefreshToken(raw)
            with transaction.atomic():
                OutstandingToken.objects.select_for_update().get(jti=token["jti"])
                token = RefreshToken(raw)
                user = get_user_model().objects.get(pk=token["user_id"], is_active=True)
                if token.get("hash_password") != get_md5_hash_password(user.password):
                    raise TokenError("Credenciales cambiadas.")
                token.blacklist()
                return issue_tokens(user, Response(ProfileSerializer(user).data))
        except (TokenError, get_user_model().DoesNotExist, OutstandingToken.DoesNotExist, KeyError) as exc:
            raise AuthenticationFailed("Tu sesion termino. Ingresa nuevamente.") from exc


class LogoutView(PublicAuthView):
    @extend_schema(request=None, responses={204: None}, tags=["Cuenta"])
    def post(self, request):
        try:
            RefreshToken(request.COOKIES.get(settings.REFRESH_COOKIE, "")).blacklist()
        except TokenError:
            pass
        response = Response(status=204)
        response.delete_cookie(settings.ACCESS_COOKIE, path="/", samesite="Lax")
        response.delete_cookie(settings.REFRESH_COOKIE, path="/api/auth/", samesite="Lax")
        response["Cache-Control"] = "no-store"
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ProfileSerializer, tags=["Cuenta"])
    def get(self, request):
        response = Response(ProfileSerializer(request.user).data)
        response["Cache-Control"] = "no-store"
        return response
