import uuid
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from patients.models import Patient
from cancers.models import (
    CancerType, CancerCase, Anapath, Imaging, Analysis, CancerTreatment
)

class Command(BaseCommand):
    help = 'Creates 3 complete sample cancer cases linked to an existing patient.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting generation of sample cancer cases..."))
        
        # 1. Fetch the first existing patient
        patient = Patient.objects.first()
        if not patient:
            self.stdout.write(self.style.ERROR("No Patient found in the database. Please create a patient first."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Found Patient: {patient.nom} {patient.prenom} (ID: {patient.id_malade})"))

        # 2. Define our 3 target cancer types and fetch/create them
        cancer_defs = [
            {"nom": "Cancer du Sein", "desc": "Tumeur maligne de la glande mammaire"},
            {"nom": "Cancer du Poumon", "desc": "Carcinome bronchogénique"},
            {"nom": "Cancer Colorectal", "desc": "Tumeur maligne du côlon ou du rectum"}
        ]
        
        cancer_types = {}
        for cdef in cancer_defs:
            ctype, created = CancerType.objects.get_or_create(
                nom=cdef["nom"],
                defaults={'description': cdef["desc"]}
            )
            cancer_types[cdef["nom"]] = ctype
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created CancerType: {ctype.nom}"))

        # 3. Create Cancer Cases and associated Medical Records
        
        base_date = timezone.now().date()
        
        # --- Case 1: Breast Cancer ---
        self._create_full_case(
            patient=patient,
            cancer_type=cancer_types["Cancer du Sein"],
            sous_type="Carcinome canalaire infiltrant",
            niveau="Stade IIB",
            taille_cancer="3.5 cm",
            etat="confirmé",
            dynamic_attrs={
                "stade": "IIB",
                "grade_sbr": "Grade 2",
                "resepteurs_hormonaux": "ER+ / PR+",
                "her2": "Négatif",
                "ganglions_atteints": "1/12"
            },
            anapath_data={
                "N_dossier": "ANA-2023-4589",
                "N_lecture": "L-001",
                "medecin": "Dr. Benali",
                "date_offset_days": -45,
                "report": "Carcinome canalaire infiltrant de grade SBR 2. Marges saines. Présence d'un embole vasculaire."
            },
            imaging_data=[
                {"type": "Mammographie bilatérale", "offset": -55},
                {"type": "IRM mammaire", "offset": -50}
            ],
            analysis_data=[
                {"type": "Biopsie mammaire (microbiopsie)", "offset": -48},
                {"type": "Bilan sanguin (NFS, bilan hépatique)", "offset": -40}
            ],
            treatment_data=[
                {"type": "Chirurgie (Tumorectomie + GS)", "offset": -30, "remarques": "Chirurgie conservatrice. Suites opératoires simples."},
                {"type": "Chimiothérapie (Protocole FEC-Docetaxel)", "offset": -10, "remarques": "Cure 1/6 bien tolérée."},
                {"type": "Radiothérapie", "offset": 30, "remarques": "Prévue après la fin de la chimiothérapie."}
            ]
        )

        # --- Case 2: Lung Cancer ---
        self._create_full_case(
            patient=patient,
            cancer_type=cancer_types["Cancer du Poumon"],
            sous_type="Adénocarcinome bronchique",
            niveau="Stade IIIA",
            taille_cancer="4.2 cm",
            etat="en_traitement",
            dynamic_attrs={
                "stade": "IIIA",
                "mutation_egfr": "Positive (Exon 19)",
                "alk": "Négatif",
                "pdl1": "Expression 45%",
                "ps": "1"
            },
            anapath_data={
                "N_dossier": "PNO-2023-1122",
                "N_lecture": "L-054",
                "medecin": "Dr. Khelifa",
                "date_offset_days": -120,
                "report": "Adénocarcinome moyennement différencié infiltrant la plèvre viscérale. N2 positif."
            },
            imaging_data=[
                {"type": "Scanner Thoraco-Abdomino-Pelvien (TAP)", "offset": -130},
                {"type": "TEP Scan", "offset": -125}
            ],
            analysis_data=[
                {"type": "Biopsie sous scanner", "offset": -125},
                {"type": "Biologie moléculaire (NGS)", "offset": -115}
            ],
            treatment_data=[
                {"type": "Chirurgie (Lobectomie supérieure droite)", "offset": -100, "remarques": "Exérèse complète R0. Curage ganglionnaire."},
                {"type": "Chimiothérapie adjuvante", "offset": -70, "remarques": "Cisplatine + Vinorelbine. 4 cures complétées."},
                {"type": "Thérapie Ciblée (Osimertinib)", "offset": -10, "remarques": "Début de la thérapie ciblée vu la mutation EGFR."}
            ]
        )

        # --- Case 3: Colorectal Cancer ---
        self._create_full_case(
            patient=patient,
            cancer_type=cancer_types["Cancer Colorectal"],
            sous_type="Adénocarcinome colique",
            niveau="Stade IV",
            taille_cancer="6 cm",
            etat="metastatique",
            dynamic_attrs={
                "stade": "IV",
                "localisation": "Côlon sigmoïde",
                "mutation_kras": "Muté",
                "statut_msm": "MSS",
                "metastases": "Hépatiques (bi-lobaires)"
            },
            anapath_data={
                "N_dossier": "COL-2024-0098",
                "N_lecture": "L-112",
                "medecin": "Dr. Mansouri",
                "date_offset_days": -20,
                "report": "Adénocarcinome lieberkühnien bien différencié ulcéro-bourgeonnant. Emboles présents."
            },
            imaging_data=[
                {"type": "Coloscopie totale", "offset": -30},
                {"type": "Scanner TAP", "offset": -25},
                {"type": "IRM hépatique", "offset": -22}
            ],
            analysis_data=[
                {"type": "Biopsie endoscopique", "offset": -30},
                {"type": "Marqueurs tumoraux (ACE, CA 19-9)", "offset": -25}
            ],
            treatment_data=[
                {"type": "Chirurgie (Colectomie gauche)", "offset": -15, "remarques": "Chirurgie première en urgence pour syndrome sub-occlusif."},
                {"type": "Chimiothérapie (Protocole FOLFIRI + Bevacizumab)", "offset": 5, "remarques": "Dossier validé en RCP. Cure 1 prévue la semaine prochaine."}
            ]
        )

        self.stdout.write(self.style.SUCCESS("\n🎉 Successfully generated 3 complete sample cancer cases!"))

    def _create_full_case(self, patient, cancer_type, sous_type, niveau, taille_cancer, etat, dynamic_attrs, anapath_data, imaging_data, analysis_data, treatment_data):
        self.stdout.write(f"\n--- Creating Case: {cancer_type.nom} ---")
        base_date = timezone.now().date()
        
        # 1. Create CancerCase
        cancer_case = CancerCase.objects.create(
            patient=patient,
            cancer_type=cancer_type,
            sous_type=sous_type,
            niveau=niveau,
            taille_cancer=taille_cancer,
            etat=etat,
            dynamic_attributes=dynamic_attrs,
            type_cancer=cancer_type.nom # Legacy field sync
        )
        self.stdout.write(f"  + CancerCase {cancer_case.id_cancer}")

        # 2. Create Anapath
        Anapath.objects.create(
            cancer_case=cancer_case,
            N_dossier_anapath=anapath_data["N_dossier"],
            N_lecture=anapath_data["N_lecture"],
            medecin=anapath_data["medecin"],
            date_etude=base_date + timedelta(days=anapath_data.get("date_offset_days", 0)),
            report=anapath_data["report"]
        )
        self.stdout.write(f"  + Anapath {anapath_data['N_dossier']}")

        # 3. Create Imaging
        for img in imaging_data:
            Imaging.objects.create(
                cancer_case=cancer_case,
                type_imagerie=img["type"],
                date_imagerie=base_date + timedelta(days=img.get("offset", 0))
            )
        self.stdout.write(f"  + {len(imaging_data)} Imaging records")

        # 4. Create Analysis
        for ana in analysis_data:
            Analysis.objects.create(
                cancer_case=cancer_case,
                type_analyse=ana["type"],
                date_analyse=base_date + timedelta(days=ana.get("offset", 0))
            )
        self.stdout.write(f"  + {len(analysis_data)} Analysis records")

        # 5. Create Treatments
        for trt in treatment_data:
            CancerTreatment.objects.create(
                cancer_case=cancer_case,
                type_traitement=trt["type"],
                date_traitement=base_date + timedelta(days=trt.get("offset", 0)),
                remarques=trt.get("remarques", "")
            )
        self.stdout.write(f"  + {len(treatment_data)} Treatment records")
