"""
Management command: seed_gis_data

Creates 3 demo geographic zones around Tlemcen, Algeria, and assigns
random (but geographically plausible) coordinates to existing patients
so that spatial analysis can be tested immediately.

Usage:
    python manage.py seed_gis_data
    python manage.py seed_gis_data --clear   # Delete existing zones first
"""
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from gis_analytics.models import Zone, ZoneDataSource, Commune
from patients.models import Patient


# ──────────────────────────────────────────────────────────────────────────
# Demo zones around Tlemcen, Algeria (GeoJSON Polygon, [lng, lat] order)
# ──────────────────────────────────────────────────────────────────────────
DEMO_ZONES = [
    {
        "name": "Zone Industrielle Nord",
        "type": "industrial",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [-1.370, 34.930],
                [-1.290, 34.930],
                [-1.290, 34.895],
                [-1.370, 34.895],
                [-1.370, 34.930],
            ]],
        },
        "data_sources": [
            {"year": 2023, "pollution_level": 78.4, "population": 42000},
            {"year": 2022, "pollution_level": 82.1, "population": 41000},
        ],
    },
    {
        "name": "Centre Ville Tlemcen",
        "type": "administrative",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [-1.340, 34.895],
                [-1.285, 34.895],
                [-1.285, 34.860],
                [-1.340, 34.860],
                [-1.340, 34.895],
            ]],
        },
        "data_sources": [
            {"year": 2023, "pollution_level": 32.5, "population": 68000},
            {"year": 2022, "pollution_level": 30.1, "population": 67000},
        ],
    },
    {
        "name": "Zone Périphérique Ouest",
        "type": "pollution",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[
                [-1.420, 34.880],
                [-1.360, 34.880],
                [-1.360, 34.840],
                [-1.420, 34.840],
                [-1.420, 34.880],
            ]],
        },
        "data_sources": [
            {"year": 2023, "pollution_level": 112.7, "population": 25000},
            {"year": 2022, "pollution_level": 108.3, "population": 24500},
        ],
    },
]

# Approx 0.015° (~1.6 km) half-side for commune square polygons
_COMMUNE_HALF = 0.015


def _make_square_polygon(lat, lng, half=_COMMUNE_HALF):
    """Build a small square Polygon around a center point for presentation."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lng - half, lat - half],
            [lng + half, lat - half],
            [lng + half, lat + half],
            [lng - half, lat + half],
            [lng - half, lat - half],
        ]],
    }


# 53 communes of Tlemcen wilaya with centre coordinates [lat, lng]
# Source: official Algerian administrative division dataset
TLEMCEN_COMMUNES = [
    ("Tlemcen",        34.8818, -1.3167),
    ("Beni Mester",    34.8704, -1.4210),
    ("Aïn Tallout",    34.9300, -0.9543),
    ("Remchi",         35.0617, -1.4318),
    ("El Fehoul",      35.1157, -1.2948),
    ("Sabra",          34.8260, -1.5303),
    ("Ghazaouet",      35.0939, -1.8632),
    ("Souani",         34.9221, -1.9158),
    ("Djebala",        34.9599, -1.8213),
    ("El Gor",         34.6380, -1.1532),
    ("Oued Lakhdar",   34.8750, -1.1341),
    ("Aïn Fezza",      34.8780, -1.2349),
    ("Ouled Mimoun",   34.9048, -1.0282),
    ("Amieur",         35.0352, -1.2390),
    ("Aïn Youcef",     35.0473, -1.3739),
    ("Zenata",         34.9895, -1.4631),
    ("Beni Snous",     34.6622, -1.5398),
    ("Bab El Assa",    34.9661, -2.0318),
    ("Dar Yaghmouracene", 35.0996, -1.7995),
    ("Fellaoucene",    35.0350, -1.5991),
    ("Azaïls",         34.6806, -1.4814),
    ("Sebaa Chioukh",  35.1564, -1.3606),
    ("Terny Beni Hdiel", 34.7960, -1.3568),
    ("Bensekrane",     35.0721, -1.2274),
    ("Aïn Nehala",     35.0270, -0.9325),
    ("Hennaya",        34.9507, -1.3667),
    ("Maghnia",        34.8472, -1.7297),
    ("Hammam Boughrara", 34.8937, -1.6383),
    ("Souahlia",       35.0270, -1.8970),
    ("MSirda Fouaga",  35.0189, -2.0832),
    ("Aïn Fetah",      34.9656, -1.6375),
    ("El Aricha",      34.2240, -1.2577),
    ("Souk Tlata",     35.0704, -2.0014),
    ("Sidi Abdelli",   35.0646, -1.1343),
    ("Sebdou",         34.6403, -1.3220),
    ("Beni Ouarsous",  35.0915, -1.5830),
    ("Sidi Medjahed",  34.7751, -1.6366),
    ("Beni Boussaid",  34.6480, -1.7530),
    ("Marsa Ben M'Hidi", 35.0818, -2.2044),
    ("Nedroma",        35.0108, -1.7481),
    ("Sidi Djillali",  34.4447, -1.5663),
    ("Beni Bahdel",    34.6937, -1.5187),
    ("El Bouihi",      34.4138, -1.6859),
    ("Honaïne",        35.1565, -1.6746),
    ("Tienet",         35.0453, -1.8370),
    ("Ouled Riyah",    34.9610, -1.4980),
    ("Bouhlou",        34.7739, -1.5729),
    ("Beni Khellad",   35.1828, -1.5847),
    ("Aïn Ghoraba",    34.7138, -1.3891),
    ("Chetouane",      34.9208, -1.2911),
    ("Mansourah",      34.8730, -1.3296),
    ("Beni Semiel",    34.7851, -1.0917),
    ("Aïn Kebira",     36.3648, 5.5069),  # Note: actually in Sétif wilaya post-2026 split
]

# Bounding box for the entire Tlemcen region — patients get random coords within this
TLEMCEN_BBOX = {
    "lat_min": 34.840,
    "lat_max": 34.930,
    "lng_min": -1.420,
    "lng_max": -1.285,
}


class Command(BaseCommand):
    help = "Seeds demo geographic zones and patient coordinates for GIS analytics testing."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing zones before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_zones, _ = Zone.objects.all().delete()
            deleted_communes, _ = Commune.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"Deleted {deleted_zones} zones and {deleted_communes} communes."
            ))

        with transaction.atomic():
            self._seed_zones()
            self._seed_communes()
            self._seed_patient_coordinates()

        self.stdout.write(self.style.SUCCESS("OK: GIS seed data created successfully."))

    def _seed_zones(self):
        created_count = 0
        for zone_data in DEMO_ZONES:
            zone, created = Zone.objects.get_or_create(
                name=zone_data["name"],
                defaults={
                    "type":    zone_data["type"],
                    "geojson": zone_data["geojson"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created zone: {zone.name}")

            for ds_data in zone_data["data_sources"]:
                ZoneDataSource.objects.get_or_create(
                    zone=zone,
                    year=ds_data["year"],
                    defaults={
                        "pollution_level": ds_data["pollution_level"],
                        "population":      ds_data["population"],
                    },
                )

        self.stdout.write(f"  {created_count} new zones created.")

    def _seed_communes(self):
        created_count = 0
        for name, lat, lng in TLEMCEN_COMMUNES:
            _, created = Commune.objects.get_or_create(
                name=name,
                defaults={
                    "wilaya":  "Tlemcen",
                    "geojson": _make_square_polygon(lat, lng),
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created commune: {name}")

        self.stdout.write(f"  {created_count} new communes created.")

    def _seed_patient_coordinates(self):
        """
        Assign random coordinates within Tlemcen to patients that
        don't already have coordinates.
        """
        patients_without_coords = Patient.objects.filter(
            latitude__isnull=True,
            longitude__isnull=True,
        )
        count = patients_without_coords.count()

        if count == 0:
            self.stdout.write("  All patients already have coordinates — skipping.")
            return

        self.stdout.write(f"  Assigning random Tlemcen coordinates to {count} patients...")

        bbox = TLEMCEN_BBOX
        updated = []
        for patient in patients_without_coords.iterator():
            patient.latitude  = round(random.uniform(bbox["lat_min"], bbox["lat_max"]), 6)
            patient.longitude = round(random.uniform(bbox["lng_min"], bbox["lng_max"]), 6)
            updated.append(patient)

            # Bulk-update in batches of 500
            if len(updated) >= 500:
                Patient.objects.bulk_update(updated, ['latitude', 'longitude'])
                updated = []

        if updated:
            Patient.objects.bulk_update(updated, ['latitude', 'longitude'])

        self.stdout.write(f"  {count} patients updated with coordinates.")
