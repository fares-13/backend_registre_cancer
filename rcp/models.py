import uuid
from django.db import models
from django.conf import settings
from cancers.models import CancerCase

class RcpSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Planifiée'),
        ('ongoing', 'En cours'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]

    id = models.CharField(primary_key=True, max_length=50) # e.g. RCP-2026-001
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='scheduled')
    date = models.DateField(blank=True, null=True)
    time = models.TimeField(blank=True, null=True)
    duration = models.IntegerField(help_text="Duration in minutes", blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    isOnline = models.BooleanField(default=False)
    meetingLink = models.URLField(blank=True, null=True)
    coordinator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='coordinated_rcps')
    service = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    isAllDoctors = models.BooleanField(default=False, help_text="If True, all doctors can access this RCP")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return self.title

    @property
    def casesCount(self):
        return self.cases.count()

    @property
    def participantsCount(self):
        return self.participants.count()


class RcpParticipant(models.Model):
    ROLE_CHOICES = [
        ('coordinator', 'Coordinateur'),
        ('presenter', 'Présentateur'),
        ('member', 'Membre'),
        ('invited', 'Invité'),
    ]
    STATUS_CHOICES = [
        ('confirmed', 'Confirmé'),
        ('pending', 'En attente'),
        ('declined', 'Décliné'),
        ('absent', 'Absent'),
    ]

    rcp = models.ForeignKey(RcpSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    isRequired = models.BooleanField(default=True)
    invitedAt = models.DateTimeField(auto_now_add=True)
    respondedAt = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('rcp', 'user')

class RcpCase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('discussed', 'Discuté'),
        ('deferred', 'Reporté'),
    ]

    rcp = models.ForeignKey(RcpSession, on_delete=models.CASCADE, related_name='cases')
    cancer_case = models.ForeignKey(CancerCase, on_delete=models.CASCADE)
    presenter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    order = models.IntegerField(default=1)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    duration = models.IntegerField(default=15, help_text="Planned duration in minutes")
    notes = models.TextField(blank=True, null=True)
    documents = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

class RcpDecision(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('validated', 'Validée'),
        ('implemented', 'Appliquée'),
        ('cancelled', 'Annulée'),
    ]

    rcp = models.ForeignKey(RcpSession, on_delete=models.CASCADE, related_name='decisions')
    rcp_case = models.OneToOneField(RcpCase, on_delete=models.CASCADE, related_name='decision')
    decision = models.TextField()
    decisionType = models.CharField(max_length=100)
    rationale = models.TextField(blank=True, null=True)
    followUp = models.TextField(blank=True, null=True)
    followUpDate = models.DateField(blank=True, null=True)
    validatedBy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='validated_decisions')
    validatedAt = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    implementedAt = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class RcpTemplate(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100)
    specialty = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    sections = models.JSONField(default=list)
    isDefault = models.BooleanField(default=False)
    usageCount = models.IntegerField(default=0)
    createdBy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class RcpProtocol(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('final', 'Final'),
        ('signed', 'Signé'),
    ]

    rcp = models.OneToOneField(RcpSession, on_delete=models.CASCADE, related_name='protocol')
    title = models.CharField(max_length=300)
    content = models.TextField()
    generatedBy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='generated_protocols')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    signedBy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='signed_protocols')
    signedAt = models.DateTimeField(blank=True, null=True)
    fileUrl = models.FileField(upload_to='rcp_protocols/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class RcpMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rcp = models.ForeignKey(RcpSession, on_delete=models.CASCADE, related_name='messages')
    rcp_case = models.ForeignKey(RcpCase, on_delete=models.CASCADE, blank=True, null=True, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    type = models.CharField(max_length=50, default='text')
    attachments = models.JSONField(default=list, blank=True)
    reactions = models.JSONField(default=list, blank=True)
    isEdited = models.BooleanField(default=False)
    isPinned = models.BooleanField(default=False)
    readBy = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class RcpNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_message', 'Nouveau message'),
        ('participant_added', 'Participant ajouté'),
        ('case_added', 'Cas ajouté'),
        ('status_changed', 'Changement de statut'),
        ('report_generated', 'Compte-rendu généré'),
        ('report_signed', 'Compte-rendu signé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rcp = models.ForeignKey(RcpSession, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rcp_notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"
