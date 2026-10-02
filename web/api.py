"""Contrato comun de errores, paginacion y entrada estricta."""
from collections.abc import Mapping

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"

    def __init__(self, message, code="conflict", details=None):
        super().__init__({"code": code, "message": message, "details": details or {}}, code=code)


class StrictInputMixin:
    """No aceptar privilegios, precios o estados ocultos entre campos desconocidos."""
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            allowed = {name for name, field in self.fields.items() if not field.read_only}
            extra = set(data) - allowed
            if extra:
                raise serializers.ValidationError({key: "Este campo no es editable." for key in sorted(extra)})
        return super().to_internal_value(data)


class StandardPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100


def api_exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        exc = Conflict("Este registro tiene compras o dependencias. Puedes archivarlo, no eliminarlo.", "protected")
    elif isinstance(exc, IntegrityError):
        exc = Conflict("El registro ya existe o incumple una restriccion de datos.", "integrity")
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, Conflict):
        return response
    data = response.data
    message = data.get("detail") if isinstance(data, dict) else None
    response.data = {
        "code": getattr(exc, "default_code", "invalid"),
        "message": str(message or "Revisa los datos indicados."),
        "errors": {} if message else data,
    }
    return response
