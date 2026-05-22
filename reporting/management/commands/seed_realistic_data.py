import random
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from shapely.geometry import shape, Point, Polygon
import numpy as np

from patients.models import Patient
from cancers.models import CancerCase, CancerType
from gis_analytics.models import Zone, ZoneDataSource

class Command(BaseCommand):
    help = "Seeds realistic Algerian cancer registry data with spatial distributions."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=150, help='Number of patients to generate')
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')

    def handle(self, *args, **options):
        fake = Faker(['fr_FR', 'ar_AA'])
        count = options['count']

        if options['clear']:
            self.stdout.write(self.style.WARNING("Clearing existing patients and cases..."))
            CancerCase.objects.all().delete()
            Patient.objects.all().delete()

        # 1. Ensure Cancer Types exist
        ct_lung, _ = CancerType.objects.get_or_create(nom="Poumon", defaults={"description": "Cancer bronchique"})
        ct_breast, _ = CancerType.objects.get_or_create(nom="Sein", defaults={"description": "Cancer du sein"})
        ct_colorectal, _ = CancerType.objects.get_or_create(nom="Colorectal", defaults={"description": "Cancer colorectal"})
        
        cancer_types = [ct_lung, ct_breast, ct_colorectal]

        # 2. Map existing zones
        zones = list(Zone.objects.all())
        if not zones:
            self.stdout.write(self.style.ERROR("No zones found. Run seed_gis_data first."))
            return

        industrial_zone = next((z for z in zones if z.type == 'industrial'), None)
        center_zone     = next((z for z in zones if z.type == 'administrative'), None)
        pollution_zone  = next((z for z in zones if z.type == 'pollution'), None)

        def get_random_point_in_geojson(geojson):
            # Flatten coordinates if needed
            coords = geojson['coordinates'][0]
            poly = Polygon(coords)
            minx, miny, maxx, maxy = poly.bounds
            while True:
                p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
                if poly.contains(p):
                    return p.y, p.x  # lat, lng

        self.stdout.write(f"Generating {count} patients...")

        with transaction.atomic():
            patients_created = 0
            for i in range(count):
                # Pick a zone to place the patient in (biased)
                # 40% Industrial, 40% Center, 20% Pollution/Other
                zone = random.choices(
                    [industrial_zone, center_zone, pollution_zone],
                    weights=[40, 40, 20]
                )[0]

                lat, lng = get_random_point_in_geojson(zone.geojson)

                # Patient details
                sexe = random.choice(['M', 'F'])
                first_name = fake.first_name_male() if sexe == 'M' else fake.first_name_female()
                last_name = fake.last_name().upper()
                
                patient = Patient.objects.create(
                    numero_dossier=f"SYN-{i+1:04d}-{random.randint(1000, 9999)}",
                    nom=last_name,
                    prenom=first_name,
                    sexe=sexe,
                    date_naissance=fake.date_of_birth(minimum_age=25, maximum_age=85),
                    adresse=f"{fake.street_name()}, {zone.name}",
                    latitude=lat,
                    longitude=lng,
                    deces=random.random() < 0.15 # 15% mortality rate
                )

                # Assign Cancer Type based on zone
                if zone == industrial_zone:
                    # Higher lung cancer in industrial zones
                    ct = random.choices([ct_lung, ct_breast, ct_colorectal], weights=[60, 20, 20])[0]
                elif sexe == 'F':
                    # Higher breast cancer for females
                    ct = random.choices([ct_lung, ct_breast, ct_colorectal], weights=[10, 80, 10])[0]
                else:
                    ct = random.choice(cancer_types)

                CancerCase.objects.create(
                    patient=patient,
                    cancer_type=ct,
                    type_cancer=ct.nom, # Sync legacy field
                    etat='valide',
                    created_at=fake.date_time_between(start_date='-2y', end_date='now', tzinfo=timezone.get_current_timezone())
                )
                
                patients_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {patients_created} realistic patients and cases."))
