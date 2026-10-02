"""Montos enteros en pesos chilenos, sin conversiones con float."""
from django import template

register = template.Library()


@register.filter
def clp(value):
    return "$" + f"{int(value or 0):,}".replace(",", ".")
