"""Registra la descripcion de nuestra autenticacion en OpenAPI."""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        from . import schema  # noqa: F401
