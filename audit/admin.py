from django.contrib import admin

from audit.models import AuditLog
from directory.admin_base import ViewOnlyAdmin


@admin.register(AuditLog)
class AuditLogAdmin(ViewOnlyAdmin):
    """Always read-only: audit rows are never edited or deleted."""

    list_display = (
        "created_at",
        "action",
        "entity_type",
        "entity_id",
        "actor",
        "system_actor",
        "change_request",
    )
    list_filter = ("action", "entity_type", "system_actor")
    search_fields = ("entity_id", "actor__employee_code", "system_actor")
    list_select_related = ("actor", "change_request")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
