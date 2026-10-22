"""Writing audit rows (B.10, D-14, D-22)."""

import json
from itertools import batched

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Case, DateTimeField, Value, When

from audit.models import AuditLog

BATCH_SIZE = 500


def _jsonable(value):
    """Turn dates, decimals etc. into plain JSON values."""
    if value is None:
        return None
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def build(
    action,
    entity_type,
    entity_id,
    *,
    actor=None,
    system_actor="",
    before=None,
    after=None,
    change_request=None,
    at=None,
):
    """An unsaved AuditLog row. Exactly one of actor (an Employee) or system_actor is required.

    `at` back-dates created_at; used only when building historical demo data.
    """
    if (actor is None) == (not system_actor):
        raise ValueError("An audit row needs exactly one of actor or system_actor (D-14).")
    row = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor=actor,
        system_actor=system_actor,
        before=_jsonable(before),
        after=_jsonable(after),
        change_request=change_request,
    )
    row.backdate_to = at
    return row


def bulk_record(rows):
    """Save rows made by build(), then apply any back-dated created_at values."""
    created = AuditLog.objects.bulk_create(rows, batch_size=BATCH_SIZE)
    backdate(
        AuditLog, "created_at", {row.pk: row.backdate_to for row in created if row.backdate_to}
    )
    for row in created:
        if row.backdate_to:
            row.created_at = row.backdate_to
    return created


def record(*args, **kwargs):
    """Write one AuditLog row now. Same arguments as build()."""
    return bulk_record([build(*args, **kwargs)])[0]


def backdate(model, field_name, timestamps):
    """Overwrite an auto_now_add field for many rows: {pk: datetime}. Demo history only."""
    for chunk in batched(timestamps.items(), BATCH_SIZE, strict=False):
        whens = [When(pk=pk, then=Value(moment)) for pk, moment in chunk]
        model.objects.filter(pk__in=[pk for pk, _ in chunk]).update(
            **{field_name: Case(*whens, output_field=DateTimeField())}
        )
