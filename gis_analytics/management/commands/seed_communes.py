"""
Management command: seed_communes

Seeds simplified commune boundary polygons for the Tlemcen wilaya.
Each commune is stored as a GeoJSON Polygon (bounding box approximation).

Usage:
    python manage.py seed_communes
    python manage.py seed_communes --clear
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from gis_analytics.models import Commune

COMMUNES = [
    # Tlemcen city and immediate surroundings
    {"name": "Tlemcen", "wilaya": "Tlemcen", "lng_min": -1.350, "lng_max": -1.285, "lat_min": 34.855, "lat_max": 34.905},
    {"name": "Mansourah", "wilaya": "Tlemcen", "lng_min": -1.370, "lng_max": -1.320, "lat_min": 34.850, "lat_max": 34.885},
    {"name": "Chetouane", "wilaya": "Tlemcen", "lng_min": -1.320, "lng_max": -1.270, "lat_min": 34.900, "lat_max": 34.940},
    {"name": "Beni Mester", "wilaya": "Tlemcen", "lng_min": -1.440, "lng_max": -1.380, "lat_min": 34.845, "lat_max": 34.880},
    {"name": "Hennaya", "wilaya": "Tlemcen", "lng_min": -1.380, "lng_max": -1.320, "lat_min": 34.920, "lat_max": 34.960},
    # Northern communes
    {"name": "Remchi", "wilaya": "Tlemcen", "lng_min": -1.450, "lng_max": -1.390, "lat_min": 35.040, "lat_max": 35.080},
    {"name": "Bensekrane", "wilaya": "Tlemcen", "lng_min": -1.240, "lng_max": -1.180, "lat_min": 35.050, "lat_max": 35.090},
    {"name": "Sabra", "wilaya": "Tlemcen", "lng_min": -1.560, "lng_max": -1.490, "lat_min": 34.810, "lat_max": 34.850},
    {"name": "Ghazaouet", "wilaya": "Tlemcen", "lng_min": -1.890, "lng_max": -1.830, "lat_min": 35.070, "lat_max": 35.110},
    {"name": "Maghnia", "wilaya": "Tlemcen", "lng_min": -1.760, "lng_max": -1.690, "lat_min": 34.840, "lat_max": 34.890},
    {"name": "Nedroma", "wilaya": "Tlemcen", "lng_min": -1.780, "lng_max": -1.720, "lat_min": 34.990, "lat_max": 35.030},
    # Eastern communes
    {"name": "Ouled Mimoun", "wilaya": "Tlemcen", "lng_min": -1.070, "lng_max": -1.010, "lat_min": 34.890, "lat_max": 34.930},
    {"name": "Sidi Abdelli", "wilaya": "Tlemcen", "lng_min": -1.150, "lng_max": -1.090, "lat_min": 34.950, "lat_max": 34.990},
    {"name": "Bab El Assa", "wilaya": "Tlemcen", "lng_min": -2.060, "lng_max": -2.000, "lat_min": 34.950, "lat_max": 34.990},
    {"name": "Marsa Ben M'Hidi", "wilaya": "Tlemcen", "lng_min": -2.100, "lng_max": -2.040, "lat_min": 35.060, "lat_max": 35.100},
    {"name": "Ain Talout", "wilaya": "Tlemcen", "lng_min": -1.050, "lng_max": -0.990, "lat_min": 34.920, "lat_max": 34.960},
    {"name": "Beni Snous", "wilaya": "Tlemcen", "lng_min": -1.580, "lng_max": -1.520, "lat_min": 34.640, "lat_max": 34.680},
    {"name": "Fellaoucene", "wilaya": "Tlemcen", "lng_min": -1.620, "lng_max": -1.560, "lat_min": 34.880, "lat_max": 34.920},
    {"name": "Honaine", "wilaya": "Tlemcen", "lng_min": -1.470, "lng_max": -1.410, "lat_min": 35.120, "lat_max": 35.160},
    {"name": "Sebdou", "wilaya": "Tlemcen", "lng_min": -1.350, "lng_max": -1.290, "lat_min": 34.630, "lat_max": 34.670},
]


def _bbox_to_polygon(lng_min, lng_max, lat_min, lat_max):
    return {
        "type": "Polygon",
        "coordinates": [[
            [lng_min, lat_min],
            [lng_max, lat_min],
            [lng_max, lat_max],
            [lng_min, lat_max],
            [lng_min, lat_min],
        ]],
    }


class Command(BaseCommand):
    help = "Seeds simplified Tlemcen commune boundary polygons."

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete existing communes before seeding.')

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = Commune.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing communes."))

        with transaction.atomic():
            created_count = 0
            for c in COMMUNES:
                _, created = Commune.objects.get_or_create(
                    name=c["name"],
                    wilaya=c["wilaya"],
                    defaults={
                        "geojson": _bbox_to_polygon(
                            c["lng_min"], c["lng_max"],
                            c["lat_min"], c["lat_max"],
                        ),
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  Created commune: {c['name']}")

            self.stdout.write(self.style.SUCCESS(f"OK: {created_count} communes seeded."))
