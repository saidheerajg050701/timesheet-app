import pytest
from django.urls import reverse

from audit.models import AuditLog
from audit.services.log import record
from directory.models import User
from tests.factories import TimeEntryFactory, UserFactory
from timesheets.models import ChangeRequest, PeriodApproval, Timesheet

VIEW_ONLY_MODELS = (  # Team, Employee and Project became editable in Phase 11 (D-87)
    User,
    Timesheet,
    PeriodApproval,
    ChangeRequest,
    AuditLog,
)


@pytest.fixture
def sample_data(db):
    entry = TimeEntryFactory()
    sheet = entry.timesheet
    request = ChangeRequest.objects.create(timesheet=sheet, requester=sheet.employee, reason="x")
    approval = PeriodApproval.objects.create(employee=sheet.employee, period_start=sheet.week_start)
    record(AuditLog.Action.CREATE, "Timesheet", sheet.pk, system_actor="seed_demo")
    return {Timesheet: sheet, ChangeRequest: request, PeriodApproval: approval}


def admin_url(model, view, *args):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}", args=args)


def test_every_model_is_browsable_but_view_only(admin_client, sample_data):
    """Helper check: workflow models are listed and viewable, but never added or changed (D-87)."""
    for model in VIEW_ONLY_MODELS:
        assert admin_client.get(admin_url(model, "changelist")).status_code == 200
        assert admin_client.get(admin_url(model, "add")).status_code == 403
        obj = model.objects.first()
        change_url = admin_url(model, "change", obj.pk)
        page = admin_client.get(change_url)
        assert page.status_code == 200
        assert b'name="_save"' not in page.content
        assert admin_client.post(change_url, {}).status_code == 403
        assert admin_client.get(admin_url(model, "delete", obj.pk)).status_code == 403


def test_timesheet_page_shows_its_entries(admin_client, sample_data):
    """Helper check: the timesheet page lists its time entries."""
    sheet = sample_data[Timesheet]
    page = admin_client.get(admin_url(Timesheet, "change", sheet.pk)).content.decode()
    assert "Time entries" in page and "480" in page


def test_user_page_shows_masked_argon2_summary_only(admin_client):
    """Helper check: the password shows as an Argon2 summary, never the hash itself."""
    user = UserFactory()
    page = admin_client.get(admin_url(User, "change", user.pk)).content.decode()
    algorithm, variety, version, params, salt, hash_ = user.password.split("$")
    assert "algorithm: argon2" in page
    assert salt not in page and hash_ not in page and user.password not in page


@pytest.mark.django_db
def test_non_admin_cannot_open_admin(client, user):
    """Helper check: a logged-in employee without is_admin gets 403 at once, no login loop."""
    client.force_login(user)
    assert client.get(reverse("admin:index")).status_code == 403
    assert client.get(reverse("admin:login")).status_code == 403


@pytest.mark.django_db
def test_admin_login_uses_the_app_login_page(client, user):
    """Helper check: /admin/login/ sends anonymous users to /login/ and keeps ?next."""
    response = client.get(reverse("admin:login") + "?next=/admin/directory/employee/")
    assert response.url == "/login/?next=/admin/directory/employee/"
    assert client.get(reverse("admin:login")).url == "/login/?next=/admin/"
