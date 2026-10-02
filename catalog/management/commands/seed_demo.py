"""Datos sinteticos idempotentes para una instalacion nueva; no es un importador."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from catalog.models import Venue, Event, Sector, Price


class Command(BaseCommand):
    help = "Agrega seis eventos ficticios sin modificar registros existentes ni crear usuarios."

    @transaction.atomic
    def handle(self, *args, **options):
        venues = []
        for name, city, address in [("Parque Horizonte", "Santiago", "Avenida del Parque 1200"),
                                    ("Teatro del Puerto", "Valparaiso", "Calle del Puerto 540"),
                                    ("Centro Cultural Sur", "Concepcion", "Avenida Central 800")]:
            venue, _ = Venue.objects.get_or_create(name=name, city=city, defaults={"address": address})
            venues.append(venue)
        examples = [("Horizonte en vivo", "Los Horizontes", "live", 0, 24, 28000),
                    ("Frecuencia abierta", "Luz Vector", "electronic", 0, 38, 35000),
                    ("Cuerdas del puerto", "Elena Mar", "acoustic", 1, 19, 18000),
                    ("Sur electrico", "Rutas del Sur", "live", 2, 45, 24000),
                    ("Noche de sintetizadores", "Circuito Abierto", "electronic", 1, 56, 32000),
                    ("Sesiones cercanas", "Elena Mar Trio", "acoustic", 2, 63, 16000)]
        count = 0
        for index, (name, artist, art, venue_index, days, amount) in enumerate(examples, 1):
            starts = (timezone.localtime() + timedelta(days=days)).replace(hour=20, minute=0, second=0, microsecond=0)
            event, created = Event.objects.get_or_create(slug=f"demo-{index}", defaults={
                "name": name, "artist": artist, "artwork": art, "venue": venues[venue_index], "starts_at": starts,
                "status": Event.Status.PUBLISHED,
                "description": "Una noche para encontrarnos con la musica en vivo. Apertura de puertas una hora antes del concierto. Localidades sin asientos numerados; el ingreso se valida con una entrada individual.\n\nEvento ficticio creado para demostrar el funcionamiento del proyecto academico. No corresponde a una venta ni a un recinto real.",
            })
            if created:
                for sector_name, capacity, price in [("Cancha general", 180, amount), ("Preferencial", 60, amount + 14000)]:
                    sector = Sector.objects.create(event=event, name=sector_name, capacity=capacity)
                    Price.objects.create(sector=sector, amount=price)
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Catalogo listo: {count} eventos de demostracion agregados. No se crearon usuarios."))
