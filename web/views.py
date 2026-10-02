"""Vistas HTML: separadas de los endpoints y protegidas con el mismo JWT."""
from functools import wraps
from io import BytesIO
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, F, Sum
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_GET
import qrcode

from catalog.models import Event, Sector, Venue
from catalog.views import event_queryset
from catalog.serializers import EventSerializer
from sales.models import Purchase, PurchaseLine, Ticket
from sales.views import purchase_queryset
from .forms import VenueForm, EventForm, SectorForm


def private(organizer=False):
    def decorator(view):
        @wraps(view)
        @never_cache
        @ensure_csrf_cookie
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # La pagina vacia intenta renovar el JWT antes de solicitar otro ingreso.
                return render(request, "auth/recover.html", status=401)
            if organizer and not request.user.is_organizer:
                return error_page(request, 403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


@ensure_csrf_cookie
@require_GET
def home(request):
    return render(request, "shop/home.html", {"cities": Venue.objects.filter(active=True).values_list("city", flat=True).distinct().order_by("city")})


@ensure_csrf_cookie
@require_GET
def event_detail(request, pk):
    qs = event_queryset()
    if not (request.user.is_authenticated and request.user.is_organizer):
        qs = qs.filter(status=Event.Status.PUBLISHED, venue__active=True)
    event = get_object_or_404(qs, pk=pk)
    return render(request, "shop/event.html", {"event": event, "details": EventSerializer(event).data})


@ensure_csrf_cookie
@never_cache
@require_GET
def auth_page(request, register=False):
    if request.user.is_authenticated:
        return redirect("web:manage-home" if request.user.is_organizer else "web:home")
    return render(request, "auth/form.html", {"register": register})


@private()
@require_GET
def cart(request):
    if request.user.is_organizer:
        return error_page(request, 403)
    return render(request, "shop/cart.html")


@private()
@require_GET
def purchases(request):
    return render(request, "shop/purchases.html")


@private()
@require_GET
def my_tickets(request):
    if request.user.is_organizer:
        return error_page(request, 403)
    return render(request, "shop/tickets.html")


@private()
@require_GET
def purchase_detail(request, pk):
    qs = purchase_queryset()
    if not request.user.is_organizer:
        qs = qs.filter(user=request.user)
    purchase = get_object_or_404(qs, pk=pk)
    return render(request, "shop/purchase.html", {"purchase": purchase})


@private()
@require_GET
def ticket_detail(request, pk, qr=False):
    qs = Ticket.objects.select_related("line__purchase__user", "line__price__sector__event__venue")
    if not request.user.is_organizer:
        qs = qs.filter(line__purchase__user=request.user)
    ticket = get_object_or_404(qs, pk=pk)
    if qr:
        output = BytesIO()
        qrcode.make(str(ticket.pk)).save(output, format="PNG")
        output.seek(0)
        response = FileResponse(output, content_type="image/png")
        response["Cache-Control"] = "private, no-store"
        return response
    return render(request, "shop/ticket.html", {"ticket": ticket})


@private(organizer=True)
@require_GET
def manage_home(request):
    paid = Purchase.objects.filter(status__in=["PAGADO", "ENTREGADO"])
    return render(request, "manage/home.html", {
        "events_count": Event.objects.filter(status="PUBLICADO").count(),
        "tickets_count": Ticket.objects.filter(line__purchase__in=paid).count(),
        "pending_count": Purchase.objects.filter(status="PENDIENTE").count(),
        "revenue": PurchaseLine.objects.filter(purchase__in=paid).aggregate(n=Sum(F("quantity") * F("price__amount")))["n"] or 0,
        "recent": purchase_queryset()[:6],
    })


RESOURCES = {"recintos": (Venue, VenueForm, "Recinto"), "eventos": (Event, EventForm, "Evento"), "sectores": (Sector, SectorForm, "Localidad")}


@private(organizer=True)
@require_GET
def manage_list(request, kind):
    if kind not in RESOURCES:
        return error_page(request, 404)
    return render(request, "manage/list.html", {"kind": kind})


@private(organizer=True)
@require_GET
def manage_form(request, kind, pk=None):
    if kind not in RESOURCES:
        return error_page(request, 404)
    model, form_type, title = RESOURCES[kind]
    instance = get_object_or_404(model, pk=pk) if pk else None
    initial = {"event": request.GET.get("evento")} if kind == "sectores" else {}
    form = form_type(instance=instance, initial=initial)
    return render(request, "manage/form.html", {"kind": kind, "form": form, "instance": instance, "resource_name": title})


@private(organizer=True)
@require_GET
def manage_sales(request):
    return render(request, "manage/sales.html")


@private(organizer=True)
@require_GET
def manage_admission(request):
    return render(request, "manage/admission.html", {"events": Event.objects.exclude(status="BORRADOR")})


@private(organizer=True)
@require_GET
def docs(request):
    return render(request, "manage/docs.html")


def error_page(request, code=404):
    labels = {400: "Solicitud no valida", 403: "Acceso restringido", 404: "Esta pagina no esta en cartelera", 500: "Necesitamos un momento"}
    message = labels.get(code, "No pudimos completar la solicitud")
    if request.path.startswith("/api/"):
        return JsonResponse({"code": str(code), "message": message}, status=code)
    return render(request, "errors/error.html", {"error_code": code, "error_title": message}, status=code)


@csrf_exempt
def not_found(request, exception=None, path=None):
    # No modifica datos: una ruta inexistente siempre debe responder 404.
    return error_page(request, 404)


def forbidden(request, exception=None):
    return error_page(request, 403)


def bad_request(request, exception=None):
    return error_page(request, 400)


def server_error(request):
    return error_page(request, 500)


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return JsonResponse({"code": "csrf_failed", "message": "La verificacion de seguridad vencio. Recarga la pagina."}, status=403)
    return error_page(request, 403)
