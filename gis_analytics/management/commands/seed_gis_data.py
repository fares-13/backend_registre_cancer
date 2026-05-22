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

from gis_analytics.models import Zone, ZoneDataSource
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
            deleted, _ = Zone.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing zones."))

        with transaction.atomic():
            self._seed_zones()
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
