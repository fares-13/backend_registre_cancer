from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        # Patient
        CREATE_PATIENT = "create_patient", "Création patient"
        UPDATE_PATIENT = "update_patient", "Modification patient"
        DELETE_PATIENT = "delete_patient", "Suppression patient"
        DUPLICATE_PATIENT = "duplicate_patient", "Fusion doublon patient"
        # Cancer Case
        CREATE_CASE = "create_case", "Création cas cancer"
        UPDATE_CASE = "update_case", "Modification cas cancer"
        DELETE_CASE = "delete_case", "Suppression cas cancer"
        # Documents
        UPLOAD_DOCUMENT = "upload_document", "Upload document"
        DELETE_DOCUMENT = "delete_document", "Suppression document"
        PREVIEW_DOCUMENT = "preview_document", "Prévisualisation document"
        DOWNLOAD_DOCUMENT = "download_document", "Téléchargement document"
        # Auth
        LOGIN = "login", "Connexion"
        LOGOUT = "logout", "Déconnexion"
        FAILED_LOGIN = "failed_login", "Échec connexion"
        # Follow-up
        ADD_FOLLOWUP = "add_followup", "Ajout suivi"
        MODIFY_FOLLOWUP = "modify_followup", "Modification suivi"
        # Treatment
        ADD_TREATMENT = "add_treatment", "Ajout traitement"
        UPDATE_TREATMENT = "update_treatment", "Modification traitement"
        # Users
        CREATE_USER = "create_user", "Création utilisateur"
        UPDATE_USER = "update_user", "Modification utilisateur"
        DELETE_USER = "delete_user", "Suppression utilisateur"

    class EntityType(models.TextChoices):
        PATIENT = "patient", "Patient"
        CANCER_CASE = "cancer_case", "Cas cancer"
        DOCUMENT = "document", "Document"
        USER = "user", "Utilisateur"
        FOLLOWUP = "followup", "Suivi"
        TREATMENT = "treatment", "Traitement"
        SYSTEM = "system", "Système"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Utilisateur",
        related_name="audit_logs",
    )
    action_type = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        verbose_name="Type d'action",
        db_index=True,
    )
    entity_type = models.CharField(
        max_length=50,
        choices=EntityType.choices,
        verbose_name="Type d'entité",
        db_index=True,
    )
    entity_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="ID de l'entité",
    )
    entity_label = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Libellé de l'entité",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
    )
    route_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Chemin de la requête",
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="Adresse IP",
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User-Agent",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Métadonnées",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Date de création",
    )

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action_type", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        user_str = str(self.user) if self.user else "Anonyme"
        return f"[{self.created_at:%d/%m/%Y %H:%M}] {user_str} - {self.get_action_type_display()}"
