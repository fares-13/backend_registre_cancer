from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework import filters as drf_filters

from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogStatsSerializer
from .filters import filter_audit_logs
from accounts.permissions import IsAdmin, IsEpidemiologiste


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin | IsEpidemiologiste]
    filter_backends = [drf_filters.OrderingFilter]
    ordering_fields = ["created_at", "action_type", "user__nom"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_audit_logs(qs, self.request.query_params)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = filter_audit_logs(self.get_queryset(), request.query_params)

        total = qs.count()

        by_action = list(
            qs.values("action_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        by_user = list(
            qs.values("user__id", "user__nom", "user__prenom")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        by_date = list(
            qs.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("-date")[:30]
        )

        serializer = AuditLogStatsSerializer(data={
            "total": total,
            "by_action": by_action,
            "by_user": by_user,
            "by_date": by_date,
        })
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def recent(self, request):
        qs = self.get_queryset()[:20]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
