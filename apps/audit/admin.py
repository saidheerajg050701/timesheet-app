from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter

from apps.audit.models import AuditLog
from apps.directory.admin_base import ViewOnlyAdmin


@admin.register(AuditLog)
class AuditLogAdmin(ViewOnlyAdmin):
    """Always read-only: audit rows are never edited or deleted (D-87, D-93)."""

    list_display = (
        "created_at",
        "action",
        "entity_type",
        "entity_id",
        "actor",
        "system_actor",
        "change_request",
    )
    list_filter = (
        "action",
        "entity_type",
        ("actor", RelatedOnlyFieldListFilter),
        "system_actor",
        "created_at",
    )
    search_fields = (
        "entity_id",
        "actor__employee_code",
        "actor__first_name",
        "actor__last_name",
        "system_actor",
    )
    list_select_related = ("actor", "change_request")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
