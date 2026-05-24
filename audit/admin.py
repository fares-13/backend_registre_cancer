from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "action_type", "entity_type", "entity_label"]
    list_filter = ["action_type", "entity_type", "created_at"]
    search_fields = ["description", "entity_label", "user__nom", "user__email"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
