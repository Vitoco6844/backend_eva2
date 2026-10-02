"""API y paginas separadas; re_path es la ultima ruta de recuperacion 404."""
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import DefaultRouter
from catalog.views import VenueViewSet, EventViewSet, SectorViewSet
from sales.views import CartView, CartAddView, CartItemView, CheckoutView, PurchaseViewSet, AdmissionView
from sales.views import MyTicketsView, DirectPaymentView
from web import views

router = DefaultRouter()
router.register("recintos", VenueViewSet, basename="venue")
router.register("eventos", EventViewSet, basename="event")
router.register("sectores", SectorViewSet, basename="sector")
router.register("compras", PurchaseViewSet, basename="purchase")

urlpatterns = [
    path("api/docs/", views.docs, name="api-docs"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/auth/", include("accounts.urls")),
    path("api/carrito/", CartView.as_view()),
    path("api/carro-tickets/", CartView.as_view()),
    path("api/carrito/items/", CartAddView.as_view()),
    path("api/carrito/items/<int:pk>/", CartItemView.as_view()),
    path("api/checkout/", CheckoutView.as_view()),
    path("api/compras/pagar/", DirectPaymentView.as_view()),
    path("api/mis-entradas/", MyTicketsView.as_view()),
    path("api/entradas/validar/", AdmissionView.as_view()),
    path("api/", include((router.urls, "api"), namespace="api")),
    path("", include("web.urls")),
    # Solo imagenes previamente validadas por el servidor. Para desarrollo local.
    re_path(r"^media/(?P<path>events/.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(r"^(?P<path>.*)$", views.not_found),
]
handler404 = "web.views.not_found"
handler403 = "web.views.forbidden"
handler400 = "web.views.bad_request"
handler500 = "web.views.server_error"
