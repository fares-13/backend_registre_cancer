from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_nom = serializers.SerializerMethodField()
    user_prenom = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    temps_ecoule = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_nom",
            "user_prenom",
            "user_role",
            "action_type",
            "entity_type",
            "entity_id",
            "entity_label",
            "description",
            "route_path",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at",
            "temps_ecoule",
        ]
        read_only_fields = fields

    def get_user_nom(self, obj):
        return obj.user.nom if obj.user else "Système"

    def get_user_prenom(self, obj):
        return obj.user.prenom if obj.user else ""

    def get_user_role(self, obj):
        return obj.user.role if obj.user else "SYSTEM"

    def get_temps_ecoule(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"il y a {total_seconds}s"
        if total_seconds < 3600:
            return f"il y a {total_seconds // 60}min"
        if total_seconds < 86400:
            return f"il y a {total_seconds // 3600}h"
        return f"il y a {total_seconds // 86400}j"


class AuditLogStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_action = serializers.ListField()
    by_user = serializers.ListField()
    by_date = serializers.ListField()
