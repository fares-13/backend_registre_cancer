from django.db import models
import uuid

class Patient(models.Model):
    class Sexe(models.TextChoices):
        M = 'M', 'Masculin'
        F = 'F', 'Féminin'

    class SituationFamiliale(models.TextChoices):
        CELIBATAIRE = 'Célibataire', 'Célibataire'
        MARIE = 'Marié(e)', 'Marié(e)'
        DIVORCE = 'Divorcé(e)', 'Divorcé(e)'
        VEUF = 'Veuf(ve)', 'Veuf(ve)'

    class GroupeSanguin(models.TextChoices):
        A_PLUS = 'A+', 'A+'
        A_MOINS = 'A-', 'A-'
        B_PLUS = 'B+', 'B+'
        B_MOINS = 'B-', 'B-'
        AB_PLUS = 'AB+', 'AB+'
        AB_MOINS = 'AB-', 'AB-'
        O_PLUS = 'O+', 'O+'
        O_MOINS = 'O-', 'O-'

    id_malade = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_dossier = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    date_naissance = models.DateField()
    adresse = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    N_carte_nationale = models.CharField(max_length=50, blank=True, null=True)
    N_securite_sociale = models.CharField(max_length=50, blank=True, null=True)
    sexe = models.CharField(max_length=1, choices=Sexe.choices, blank=True, null=True)
    situation_familiale = models.CharField(max_length=20, choices=SituationFamiliale.choices, blank=True, null=True)
    nb_enfants = models.PositiveIntegerField(default=0)
    group_sanguin = models.CharField(max_length=5, choices=GroupeSanguin.choices, blank=True, null=True)
    poids = models.DecimalField(max_digits=5, decimal_places=2, help_text="Poids en kg", blank=True, null=True)
    taille = models.PositiveIntegerField(help_text="Taille en cm", blank=True, null=True)
    autre_maladie = models.TextField(blank=True, null=True)
    nb_fois_cancer = models.PositiveIntegerField(default=0)
    deces = models.BooleanField(default=False)
    date_deces = models.DateField(blank=True, null=True)
    cause = models.TextField(blank=True, null=True)
    derniere_visite = models.DateField(auto_now=True)
    
    # NEW: Static Habits Storage
    habitudes_fixes = models.JSONField(blank=True, null=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.numero_dossier})"

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

class QuestionHabitude(models.Model):
    class TypeReponse(models.TextChoices):
        BOOLEEN = 'booleen', 'Booléen (Oui/Non)'
        TEXTE = 'texte', 'Texte libre'
        NOMBRE = 'nombre', 'Nombre'
        CHOIX_MULTIPLE = 'choix_multiple', 'Choix Multiple'

    titre = models.CharField(max_length=255)
    type_reponse = models.CharField(max_length=20, choices=TypeReponse.choices, default=TypeReponse.BOOLEEN)
    options = models.JSONField(blank=True, null=True, help_text="Liste des options pour choix multiple, ex: [\"Jamais\", \"Parfois\"]")
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'id']
        verbose_name = "Question Habitude de Vie"

    def __str__(self):
        return self.titre

class ReponseHabitude(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="habitudes_reponses")
    question = models.ForeignKey(QuestionHabitude, on_delete=models.CASCADE)
    reponse = models.JSONField(blank=True, null=True, help_text="La valeur de la réponse formatée en JSON")

    class Meta:
        unique_together = ('patient', 'question')

class AntecedentFamilial(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="antecedents_familiaux")
    maladie_parent = models.CharField(max_length=255)
    age_parent = models.PositiveIntegerField(blank=True, null=True)
    parent_decede = models.BooleanField(default=False)
    cancer_parent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.maladie_parent} - Patient {self.patient.nom}"

    class Meta:
        verbose_name = "Antécédent Familial"
        verbose_name_plural = "Antécédents Familiaux"

def default_expiration():
    from django.utils import timezone
    from datetime import timedelta
    return timezone.now() + timedelta(days=7)

class PatientOnboardingToken(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name="onboarding_token")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    expires_at = models.DateTimeField(default=default_expiration)
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Token for {self.patient.nom} (Used: {self.is_used})"
