from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", _("ADMIN")
        ARCHITECT = "ARCHITECT", _("ARCHITECT")
        MEDECIN = "MEDECIN", _("MEDECIN")
        EPIDEMIOLOGISTE = "EPIDEMIOLOGISTE", _("EPIDEMIOLOGISTE")

    class Sexe(models.TextChoices):
        M = "M", _("Masculin")
        F = "F", _("Féminin")

    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    email = models.EmailField(_("adresse email"), unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    n_carte_nationale = models.CharField(max_length=50, unique=True)
    sexe = models.CharField(max_length=1, choices=Sexe.choices)
    role = models.CharField(max_length=20, choices=Role.choices)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom", "prenom", "n_carte_nationale"]

    class Meta:
        verbose_name = _("utilisateur")
        verbose_name_plural = _("utilisateurs")

    def __str__(self):
        return f"{self.email} ({self.role})"


class MedecinProfile(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="profile_medecin")
    code_medecin = models.CharField(max_length=50, unique=True)
    specialite = models.CharField(max_length=100)

    def __str__(self):
        return f"Dr. {self.utilisateur.nom} - {self.code_medecin}"


class EpidemiologisteProfile(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="profile_epidemiologiste")
    id_epidemiologist = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Epidemiologiste {self.utilisateur.nom}"


class AdminSystemeProfile(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="profile_admin")
    id_admin = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Admin {self.utilisateur.nom}"


class ArchitectProfile(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name="profile_architect")

    def __str__(self):
        return f"Architecte {self.utilisateur.nom}"
