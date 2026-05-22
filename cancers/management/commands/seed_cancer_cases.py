import random
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from shapely.geometry import shape, Point, Polygon
from datetime import timedelta

from patients.models import Patient
from cancers.models import CancerCase, CancerType
from gis_analytics.models import Zone

class Command(BaseCommand):
    help = "Seeds realistic cancer cases for existing patients and adds 5 new patients."

    def handle(self, *args, **options):
        fake = Faker(['fr_FR', 'ar_AA'])
        
        # 1. Fetch dependencies
        ct_lung, _ = CancerType.objects.get_or_create(nom="Poumon", defaults={"description": "Cancer bronchique"})
        ct_breast, _ = CancerType.objects.get_or_create(nom="Sein", defaults={"description": "Cancer du sein"})
        ct_colorectal, _ = CancerType.objects.get_or_create(nom="Colorectal", defaults={"description": "Cancer colorectal"})
        
        cancer_types = {
            'lung': ct_lung,
            'breast': ct_breast,
            'colorectal': ct_colorectal
        }

        zones = list(Zone.objects.all())
        industrial_zone = next((z for z in zones if z.type == 'industrial'), None)
        
        # 2. Process existing patients
        existing_patients = Patient.objects.all()
        if not existing_patients:
            self.stdout.write(self.style.WARNING("No existing patients found. Skipping part 1."))
        else:
            self.stdout.write(f"Processing {existing_patients.count()} existing patients...")
            cases_created = 0
            
            with transaction.atomic():
                for patient in existing_patients:
                    # Decide if this patient gets a case (60% chance for seeding purposes)
                    if random.random() > 0.6:
                        continue
                    
                    # 1 or 2 cases
                    num_cases = 1 if random.random() > 0.15 else 2
                    
                    for _ in range(num_cases):
                        self._create_realistic_case(patient, cancer_types, industrial_zone, fake)
                        cases_created += 1
            
            self.stdout.write(self.style.SUCCESS(f"Created {cases_created} cases for existing patients."))

        # 3. Create 5 new patients + cases
        self.stdout.write("Creating 5 new patients + cases...")
        with transaction.atomic():
            for i in range(5):
                # Pick a random zone for new patient
                zone = random.choice(zones) if zones else None
                lat, lng = self._get_random_point_in_zone(zone) if zone else (34.88, -1.32)
                
                sexe = random.choice(['M', 'F'])
                first_name = fake.first_name_male() if sexe == 'M' else fake.first_name_female()
                last_name = fake.last_name().upper()
                
                patient = Patient.objects.create(
                    numero_dossier=f"NEW-{uuid.uuid4().hex[:6].upper()}",
                    nom=last_name,
                    prenom=first_name,
                    sexe=sexe,
                    date_naissance=fake.date_of_birth(minimum_age=30, maximum_age=80),
                    adresse=f"{fake.street_name()}, {zone.name if zone else 'Tlemcen'}",
                    latitude=lat,
                    longitude=lng
                )
                self._create_realistic_case(patient, cancer_types, industrial_zone, fake)

        self.stdout.write(self.style.SUCCESS("Successfully completed seeding of cancer cases."))

    def _create_realistic_case(self, patient, cancer_types, industrial_zone, fake):
        """Logic to create a single realistic case for a patient."""
        
        # Determine zone containment for biasing
        is_industrial = False
        if industrial_zone and patient.latitude and patient.longitude:
            poly = Polygon(industrial_zone.geojson['coordinates'][0])
            is_industrial = poly.contains(Point(patient.longitude, patient.latitude))

        # 1. Choose Cancer Type
        weights = [1, 1, 1] # lung, breast, colorectal
        
        if is_industrial:
            weights = [10, 1, 1] # Bias toward lung
        
        choices = ['lung', 'breast', 'colorectal']
        
        # Medical filtering
        if patient.sexe == 'M':
            # Remove breast cancer for males (mostly)
            choices = ['lung', 'colorectal']
            weights = [weights[0], weights[2]]
        
        # Age check (Simplified: Lung/Colorectal more likely for > 40)
        age = (timezone.now().date() - patient.date_naissance).days // 365
        if age < 40 and 'lung' in choices:
            # Shift weight away from lung if young
            idx = choices.index('lung')
            weights[idx] = 0.1
            
        selected_key = random.choices(choices, weights=weights)[0]
        ct = cancer_types[selected_key]

        # 2. Case Details
        niveau = random.choice(['Stade I', 'Stade II', 'Stade III', 'Stade IV'])
        etat = random.choices(['confirmé', 'en_attente'], weights=[80, 20])[0]
        
        # Sub-types
        st_map = {
            'lung': ['Adénocarcinome', 'Carcinome épidermoïde', 'À petites cellules'],
            'breast': ['Canalaire invasif', 'Lobulaire invasif', 'In situ'],
            'colorectal': ['Adénocarcinome', 'Mucineux', 'Signet ring cell']
        }
        sous_type = random.choice(st_map.get(selected_key, ['Classique']))

        # Diagnostic Date (last 2 years)
        diag_date = fake.date_between(start_date='-2y', end_date='today')
        
        CancerCase.objects.create(
            patient=patient,
            cancer_type=ct,
            type_cancer=ct.nom, # Sync legacy
            sous_type=sous_type,
            niveau=niveau,
            etat=etat,
            date_diagnostic=diag_date,
            dynamic_attributes={
                "taille_tumeur": f"{random.uniform(0.5, 8.0):.1f} cm",
                "grade": random.randint(1, 3),
                "recepteurs_hormonaux": "Positif" if selected_key == 'breast' and random.random() > 0.3 else "N/A"
            },
            created_at=timezone.now()
        )

    def _get_random_point_in_zone(self, zone):
        coords = zone.geojson['coordinates'][0]
        poly = Polygon(coords)
        minx, miny, maxx, maxy = poly.bounds
        while True:
            p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
            if poly.contains(p):
                return p.y, p.x  # lat, lng
