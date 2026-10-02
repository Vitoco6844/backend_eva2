"""Controles HTML; la API vuelve a validar cada campo recibido."""
from django import forms
from catalog.models import Venue, Event, Sector


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "city", "address", "active"]
        labels = {"name": "Nombre del recinto", "city": "Ciudad", "address": "Direccion", "active": "Recinto activo"}


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "artist", "venue", "starts_at", "description", "artwork", "image", "status"]
        labels = {"name": "Nombre del evento", "artist": "Artista o agrupacion", "venue": "Recinto", "starts_at": "Fecha y hora (Chile)",
                  "description": "Descripcion", "artwork": "Imagen de referencia", "image": "Imagen propia (opcional)", "status": "Estado"}
        widgets = {"starts_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}), "description": forms.Textarea(attrs={"rows": 4}), "image": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"})}


class SectorForm(forms.ModelForm):
    price = forms.IntegerField(label="Precio final CLP", min_value=1, max_value=100000000)

    class Meta:
        model = Sector
        fields = ["event", "name", "capacity", "price", "active"]
        labels = {"event": "Evento", "name": "Nombre de la localidad", "capacity": "Capacidad total", "active": "Localidad activa"}
        widgets = {"capacity": forms.NumberInput(attrs={"min": 0, "max": 1000000})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            latest = self.instance.prices.first()
            self.fields["price"].initial = latest.amount if latest else None
            self.fields["event"].disabled = True
