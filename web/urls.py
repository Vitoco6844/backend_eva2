"""Nombres HTML propios; ningun enlace de navegacion apunta a una lista JSON."""
from django.urls import path
from . import views

app_name = "web"
urlpatterns = [
    path("", views.home, name="home"),
    path("eventos/<int:pk>/", views.event_detail, name="event"),
    path("ingresar/", views.auth_page, name="login"),
    path("registrarse/", views.auth_page, {"register": True}, name="register"),
    path("carrito/", views.cart, name="cart"),
    path("mis-compras/", views.purchases, name="purchases"),
    path("mis-entradas/", views.my_tickets, name="tickets"),
    path("compras/<uuid:pk>/", views.purchase_detail, name="purchase"),
    path("entradas/<uuid:pk>/", views.ticket_detail, name="ticket"),
    path("entradas/<uuid:pk>/qr/", views.ticket_detail, {"qr": True}, name="ticket-qr"),
    path("gestion/", views.manage_home, name="manage-home"),
    path("gestion/ventas/", views.manage_sales, name="manage-sales"),
    path("gestion/acceso/", views.manage_admission, name="manage-admission"),
    path("gestion/<str:kind>/nuevo/", views.manage_form, name="manage-create"),
    path("gestion/<str:kind>/<int:pk>/editar/", views.manage_form, name="manage-edit"),
    path("gestion/<str:kind>/", views.manage_list, name="manage-list"),
]
