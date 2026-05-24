from django.db.models import Q


def filter_audit_logs(queryset, params):
    action_type = params.get("action_type")
    entity_type = params.get("entity_type")
    user_id = params.get("user")
    date_from = params.get("date_from")
    date_to = params.get("date_to")
    search = params.get("search", "").strip()

    if action_type:
        queryset = queryset.filter(action_type=action_type)
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)
    if search:
        queryset = queryset.filter(
            Q(description__icontains=search) |
            Q(entity_label__icontains=search) |
            Q(user__nom__icontains=search) |
            Q(user__prenom__icontains=search) |
            Q(user__email__icontains=search)
        )
    return queryset
