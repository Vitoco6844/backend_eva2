"""Configuracion por entorno; PostgreSQL es obligatorio, sin fallback a SQLite."""
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)
SECRET_KEY = env("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("Falta una DJANGO_SECRET_KEY segura. Ejecuta scripts/configurar.ps1.")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "rest_framework",
    "rest_framework_simplejwt.token_blacklist", "django_filters", "drf_spectacular",
    "drf_spectacular_sidecar", "accounts.apps.AccountsConfig", "catalog",
    "sales", "web",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.JWTUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "pulso.urls"
WSGI_APPLICATION = "pulso.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "web.context.site_context",
    ]},
}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql", "NAME": env("DB_NAME"),
    "USER": env("DB_USER"), "PASSWORD": env("DB_PASSWORD"),
    "HOST": env("DB_HOST", default="127.0.0.1"), "PORT": env("DB_PORT", default="55432"),
    "CONN_MAX_AGE": 0, "OPTIONS": {"connect_timeout": 5},
}}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Permite desarrollo local con errores propios, sin depender de DEBUG=True.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MANIFEST_STRICT = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.CookieJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "web.api.StandardPagination", "PAGE_SIZE": 12,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "web.api.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"auth": "20/min"},
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True, "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_REVOKE_TOKEN": True,
}
ACCESS_COOKIE = "pulso_access"
REFRESH_COOKIE = "pulso_refresh"
COOKIE_SECURE = env.bool("COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = COOKIE_SECURE
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "web.views.csrf_failure"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SPECTACULAR_SETTINGS = {
    "TITLE": "Pulso Tickets API", "VERSION": "1.0.0",
    "DESCRIPTION": "Venta de entradas con JWT, PostgreSQL y modelo en tercera forma normal. Pago de demostracion.",
    "SERVE_PERMISSIONS": ["accounts.permissions.IsOrganizer"],
    "SERVE_AUTHENTICATION": ["accounts.authentication.CookieJWTAuthentication"],
    "SERVE_PUBLIC": False, "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR", "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "EventState": [("BORRADOR", "Borrador"), ("PUBLICADO", "Publicado"), ("ARCHIVADO", "Archivado")],
        "PurchaseState": [("PENDIENTE", "Pendiente"), ("PAGADO", "Pagado"), ("ENTREGADO", "Entregado"), ("CANCELADO", "Cancelado")],
    },
}
PAYMENT_MODE = env("PAYMENT_MODE", default="demo")
if PAYMENT_MODE != "demo":
    raise ImproperlyConfigured("Este proyecto solo admite PAYMENT_MODE=demo. No procesa cobros reales.")
STUDENT_NAME = env("STUDENT_NAME", default="Nombre completo pendiente")
STUDENT_SECTION = env("STUDENT_SECTION", default="Seccion pendiente")
STUDENT_YEAR = env("STUDENT_YEAR", default="2026")
