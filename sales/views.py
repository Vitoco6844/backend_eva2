"""Endpoints privados: nunca confian en IDs de propietario ni precios del cliente."""
from django.db.models import Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.shortcuts import get_object_or_404

from accounts.permissions import IsOrganizer, IsSpectator
from . import services
from .models import Purchase, PurchaseLine, Ticket
from .serializers import (AddItemSerializer, QuantitySerializer, CheckoutSerializer, PaymentSerializer,
                          StatusSerializer, AdmissionSerializer, PurchaseSerializer, TicketSerializer, CartSerializer)
from .serializers import DirectPaymentSerializer, MyTicketSerializer


def purchase_queryset():
    lines = PurchaseLine.objects.select_related("price__sector__event__venue").prefetch_related("tickets")
    return Purchase.objects.select_related("user").prefetch_related(Prefetch("lines", queryset=lines), "transitions__actor")


class CartView(APIView):
    permission_classes = [IsSpectator]

    @extend_schema(responses=CartSerializer, tags=["Carrito"])
    def get(self, request):
        return Response(services.cart_data(request.user))

    @extend_schema(request=AddItemSerializer, responses=CartSerializer, tags=["Carrito"])
    def post(self, request):
        data = AddItemSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(services.change_item(request.user, sector_id=data.validated_data["sector"], quantity=data.validated_data["quantity"]), status=201)

    @extend_schema(responses=CartSerializer, tags=["Carrito"])
    def delete(self, request):
        return Response(services.clear_cart(request.user))


class CartAddView(APIView):
    permission_classes = [IsSpectator]

    @extend_schema(request=AddItemSerializer, responses=CartSerializer, tags=["Carrito"])
    def post(self, request):
        data = AddItemSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(services.change_item(request.user, sector_id=data.validated_data["sector"], quantity=data.validated_data["quantity"]), status=201)


class CartItemView(APIView):
    permission_classes = [IsSpectator]

    @extend_schema(request=QuantitySerializer, responses=CartSerializer, tags=["Carrito"])
    def patch(self, request, pk):
        data = QuantitySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(services.change_item(request.user, item_id=pk, quantity=data.validated_data["quantity"]))

    @extend_schema(responses=CartSerializer, tags=["Carrito"])
    def delete(self, request, pk):
        return Response(services.change_item(request.user, item_id=pk, remove=True))


class CheckoutView(APIView):
    permission_classes = [IsSpectator]

    @extend_schema(request=CheckoutSerializer, responses={201: PurchaseSerializer, 200: PurchaseSerializer}, tags=["Compras"])
    def post(self, request):
        data = CheckoutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        purchase, created = services.checkout(request.user, **data.validated_data)
        return Response(PurchaseSerializer(purchase_queryset().get(pk=purchase.pk)).data, status=201 if created else 200)


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        queryset = purchase_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        if not self.request.user.is_organizer:
            queryset = queryset.filter(user=self.request.user)
        term = self.request.query_params.get("q", "").strip()
        if term:
            queryset = queryset.filter(Q(user__username__icontains=term) | Q(lines__price__sector__event__name__icontains=term)).distinct()
        return queryset

    @extend_schema(request=PaymentSerializer, responses=PurchaseSerializer)
    @action(detail=True, methods=["post"], url_path="pagar", permission_classes=[IsSpectator])
    def pay(self, request, pk=None):
        purchase = self.get_object()
        data = PaymentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.pay(purchase.pk, request.user, approved=data.validated_data["result"] == "approved")
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=StatusSerializer, responses=PurchaseSerializer)
    @action(detail=True, methods=["patch"], url_path="estado", permission_classes=[IsOrganizer])
    def change_status(self, request, pk=None):
        data = StatusSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.change_status(self.get_object(), request.user, target=data.validated_data["status"], reason=data.validated_data["reason"])
        return Response(self.get_serializer(self.get_object()).data)


class AdmissionView(APIView):
    permission_classes = [IsOrganizer]

    @extend_schema(request=AdmissionSerializer, responses=TicketSerializer, tags=["Entradas"])
    def post(self, request):
        data = AdmissionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ticket = services.admit(data.validated_data["ticket"], data.validated_data["event"], request.user)
        return Response(TicketSerializer(ticket).data)


class MyTicketsView(ListAPIView):
    permission_classes = [IsSpectator]
    serializer_class = MyTicketSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ticket.objects.none()
        return Ticket.objects.filter(line__purchase__user=self.request.user).select_related("line__purchase", "line__price__sector__event")


class DirectPaymentView(APIView):
    permission_classes = [IsSpectator]

    @extend_schema(request=DirectPaymentSerializer, responses=PurchaseSerializer, tags=["Compras"], operation_id="compra_pago_directo")
    def post(self, request):
        data = DirectPaymentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        purchase = get_object_or_404(Purchase, pk=data.validated_data["purchase"], user=request.user)
        services.pay(purchase.pk, request.user, approved=data.validated_data["result"] == "approved")
        return Response(PurchaseSerializer(purchase_queryset().get(pk=purchase.pk)).data)
