"""La misma regla de rol protege API, gestion HTML y Swagger."""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOrganizer(BasePermission):
    message = "Solo un organizador puede realizar esta accion."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_organizer)


class CatalogPermission(IsOrganizer):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or super().has_permission(request, view)


class IsSpectator(BasePermission):
    message = "Esta accion pertenece a una cuenta de espectador."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and not request.user.is_organizer)
