from django.contrib import admin
from .models import RcpSession, RcpParticipant, RcpCase, RcpDecision, RcpProtocol, RcpTemplate, RcpMessage, RcpNotification

@admin.register(RcpSession)
class RcpSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'date', 'status', 'service', 'coordinator']
    list_filter = ['status', 'type', 'service']
    search_fields = ['title', 'id']

@admin.register(RcpParticipant)
class RcpParticipantAdmin(admin.ModelAdmin):
    list_display = ['rcp', 'user', 'role', 'status']
    list_filter = ['role', 'status']

@admin.register(RcpCase)
class RcpCaseAdmin(admin.ModelAdmin):
    list_display = ['rcp', 'cancer_case', 'status', 'order']
    list_filter = ['status']

@admin.register(RcpDecision)
class RcpDecisionAdmin(admin.ModelAdmin):
    list_display = ['rcp', 'decisionType', 'status', 'validatedBy']
    list_filter = ['status', 'decisionType']

@admin.register(RcpProtocol)
class RcpProtocolAdmin(admin.ModelAdmin):
    list_display = ['rcp', 'title', 'status', 'generatedBy', 'signedBy']
    list_filter = ['status']

@admin.register(RcpTemplate)
class RcpTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'specialty', 'isDefault']
    list_filter = ['type', 'isDefault']

@admin.register(RcpMessage)
class RcpMessageAdmin(admin.ModelAdmin):
    list_display = ['rcp', 'sender', 'type', 'created_at', 'isPinned']
    list_filter = ['type', 'isPinned']

@admin.register(RcpNotification)
class RcpNotificationAdmin(admin.ModelAdmin):
    list_display = ['rcp', 'recipient', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
