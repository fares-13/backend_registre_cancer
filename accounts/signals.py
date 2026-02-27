from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    Utilisateur, 
    MedecinProfile, 
    EpidemiologisteProfile, 
    AdminSystemeProfile, 
    ArchitectProfile
)

@receiver(post_save, sender=Utilisateur)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == Utilisateur.Role.ADMIN:
            AdminSystemeProfile.objects.get_or_create(
                utilisateur=instance,
                id_admin=f"ADM-{instance.id or 'TMP'}"
            )
        elif instance.role == Utilisateur.Role.ARCHITECT:
            ArchitectProfile.objects.get_or_create(utilisateur=instance)
        elif instance.role == Utilisateur.Role.MEDECIN:
            MedecinProfile.objects.get_or_create(
                utilisateur=instance,
                code_medecin=f"MED-{instance.id or 'TMP'}",
                specialite="Généraliste"  # Valeur par défaut
            )
        elif instance.role == Utilisateur.Role.EPIDEMIOLOGISTE:
            EpidemiologisteProfile.objects.get_or_create(
                utilisateur=instance,
                id_epidemiologist=f"EPI-{instance.id or 'TMP'}"
            )

@receiver(post_save, sender=Utilisateur)
def save_user_profile(sender, instance, **kwargs):
    # Les profils sont gérés par create_user_profile,
    # ici on pourrait ajouter une logique de mise à jour si nécessaire.
    pass
