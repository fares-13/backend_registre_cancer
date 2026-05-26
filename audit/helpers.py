import json
from audit.models import AuditLog


def log_action(
    user,
    action_type,
    entity_type,
    entity_id="",
    entity_label="",
    description="",
    request=None,
    metadata=None,
):
    """
    Central helper to create audit log entries.

    Usage:
        log_action(
            user=request.user,
            action_type=AuditLog.ActionType.CREATE_PATIENT,
            entity_type=AuditLog.EntityType.PATIENT,
            entity_id=str(patient.id_malade),
            entity_label=f"{patient.nom} {patient.prenom}",
            description="Création d'un nouveau patient",
            request=request,
        )
    """
    ip_address = None
    route_path = ""
    user_agent = ""

    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")
        route_path = request.path
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
            entity_label=str(entity_label)[:500] if entity_label else "",
            description=str(description) if description else "",
            route_path=route_path,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )
    except Exception as exc:
        # Audit logging should not block the main request flow.
        import sys
        print(f"WARNING: failed to write audit log: {exc}", file=sys.stderr)
