from django.db import models
import uuid
from patients.models import Patient

class CancerType(models.Model):
    id_type = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200, unique=True, verbose_name="Nom du type de cancer")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Type de Cancer"
        verbose_name_plural = "Types de Cancer"

class CancerAttribute(models.Model):
    class FieldType(models.TextChoices):
        TEXT = 'text', 'Texte'
        NUMBER = 'number', 'Nombre'
        DATE = 'date', 'Date'
        BOOLEAN = 'boolean', 'Booléen (Oui/Non)'
        SELECT = 'select', 'Liste de choix'

    id_attribute = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancer_type = models.ForeignKey(CancerType, on_delete=models.CASCADE, related_name='attributes', verbose_name="Type de Cancer", null=True, blank=True, help_text="Si vide, cet attribut est considéré comme basique (pour tous les types).")
    nom_interne = models.CharField(max_length=100, help_text="Ex: 'taille_tumeur'")
    label = models.CharField(max_length=200, help_text="Ex: 'Taille de la tumeur (cm)'")
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    requis = models.BooleanField(default=False)
    options = models.JSONField(blank=True, null=True, help_text="Liste des options pour 'select', ex: [\"Option 1\", \"Option 2\"]")
    is_basic = models.BooleanField(default=False, help_text="Si coché, cet attribut apparaît pour TOUS les cancers.")

    def __str__(self):
        return f"{self.label} ({self.cancer_type.nom if self.cancer_type else 'Basique'})"

    class Meta:
        verbose_name = "Attribut de Cancer"
        verbose_name_plural = "Attributs de Cancer"

class CancerCase(models.Model):
    id_cancer = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='cancer_cases', verbose_name="Patient")
    
    cancer_type = models.ForeignKey(CancerType, on_delete=models.SET_NULL, null=True, blank=True, related_name='cases', verbose_name="Type de Cancer")
    
    # Old static fields (can be kept for legacy or migrated gradually)
    taille_cancer = models.CharField(max_length=100, blank=True, null=True, verbose_name="Taille du cancer")
    type_cancer = models.CharField(max_length=200, verbose_name="Type de cancer (Ancien)")
    sous_type = models.CharField(max_length=200, blank=True, null=True, verbose_name="Sous-type")
    niveau = models.CharField(max_length=100, blank=True, null=True, verbose_name="Niveau")
    etat = models.CharField(max_length=100, blank=True, null=True, verbose_name="État")
    classification_stade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Classification stade")
    
    # New dynamic attributes storage
    dynamic_attributes = models.JSONField(default=dict, blank=True, verbose_name="Attributs dynamiques")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cancer {self.type_cancer} - {self.patient.nom} {self.patient.prenom}"

    class Meta:
        verbose_name = "Cas de Cancer"
        verbose_name_plural = "Cas de Cancers"

class Anapath(models.Model):
    id_anapath = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancer_case = models.OneToOneField(CancerCase, on_delete=models.CASCADE, related_name='anapath', verbose_name="Cas de Cancer")
    
    N_dossier_anapath = models.CharField(max_length=100, verbose_name="N° Dossier Anapath")
    N_lecture = models.CharField(max_length=100, blank=True, null=True, verbose_name="N° Lecture")
    medecin = models.CharField(max_length=200, blank=True, null=True, verbose_name="Médecin")
    date_etude = models.DateField(blank=True, null=True, verbose_name="Date d'étude")

    def __str__(self):
        return f"Anapath {self.N_dossier_anapath}"

    class Meta:
        verbose_name = "Donnée Anapath"
        verbose_name_plural = "Données Anapaths"

class Imaging(models.Model):
    id_imagerie = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancer_case = models.ForeignKey(CancerCase, on_delete=models.CASCADE, related_name='imagings', verbose_name="Cas de Cancer")
    
    type_imagerie = models.CharField(max_length=200, verbose_name="Type d'imagerie")
    date_imagerie = models.DateField(blank=True, null=True, verbose_name="Date d'imagerie")
    document = models.FileField(upload_to='imaging/documents/', blank=True, null=True, verbose_name="Document")

    def __str__(self):
        return f"Imagerie {self.type_imagerie}"

    class Meta:
        verbose_name = "Imagerie"
        verbose_name_plural = "Imageries"

class Analysis(models.Model):
    id_analyse = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancer_case = models.ForeignKey(CancerCase, on_delete=models.CASCADE, related_name='analyses', verbose_name="Cas de Cancer")
    
    type_analyse = models.CharField(max_length=200, verbose_name="Type d'analyse")
    date_analyse = models.DateField(blank=True, null=True, verbose_name="Date d'analyse")
    document = models.FileField(upload_to='analyses/documents/', blank=True, null=True, verbose_name="Document")

    def __str__(self):
        return f"Analyse {self.type_analyse}"

    class Meta:
        verbose_name = "Analyse"
        verbose_name_plural = "Analyses"

class CancerTreatment(models.Model):
    id_traitement = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancer_case = models.ForeignKey(CancerCase, on_delete=models.CASCADE, related_name='treatments', verbose_name="Cas de Cancer")
    
    type_traitement = models.CharField(max_length=200, verbose_name="Type de traitement")
    date_traitement = models.DateField(blank=True, null=True, verbose_name="Date du traitement")
    remarques = models.TextField(blank=True, null=True, verbose_name="Remarques/Détails")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Traitement {self.type_traitement} - {self.cancer_case.patient.nom}"

    class Meta:
        verbose_name = "Traitement"
        verbose_name_plural = "Traitements"
        ordering = ['-date_traitement']
