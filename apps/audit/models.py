from django.db import models
from django.db.models import Q


class AuditLog(models.Model):
    class Action(models.TextChoices):  # full list (D-22)
        CREATE = "CREATE"
        UPDATE = "UPDATE"
        DELETE = "DELETE"
        SUBMIT = "SUBMIT"
        APPROVE = "APPROVE"
        REJECT = "REJECT"
        UNLOCK = "UNLOCK"
        PUBLISH = "PUBLISH"
        SUPERSEDE = "SUPERSEDE"
        EXPORT = "EXPORT"
        PAY = "PAY"
        SYNC = "SYNC"

    actor = models.ForeignKey("directory.Employee", null=True, blank=True, on_delete=models.PROTECT)
    system_actor = models.CharField(max_length=40, blank=True)  # e.g. "seed_demo" (D-14)
    entity_type = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=40)
    action = models.CharField(max_length=20, choices=Action.choices)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    change_request = models.ForeignKey(
        "timesheets.ChangeRequest", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(  # exactly one of actor / system_actor (D-14)
                condition=(Q(actor__isnull=False) & Q(system_actor=""))
                | (Q(actor__isnull=True) & ~Q(system_actor="")),
                name="audit_exactly_one_actor",
            )
        ]

    def __str__(self):
        who = self.actor.employee_code if self.actor_id else self.system_actor
        return f"{self.action} {self.entity_type} {self.entity_id} by {who}"
