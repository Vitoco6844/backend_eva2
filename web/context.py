"""Datos comunes para las plantillas, sin exponer configuracion sensible."""
from django.conf import settings


def site_context(request):
    return {"student_name": settings.STUDENT_NAME, "student_section": settings.STUDENT_SECTION,
            "student_year": settings.STUDENT_YEAR}
