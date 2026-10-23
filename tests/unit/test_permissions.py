import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.views import View

from directory.models import Employee
from directory.services.permissions import (
    PermissionRequiredMixin,
    can_access_payroll,
    can_approve,
    can_edit,
    can_view,
    is_manager,
    menu_for,
    reporting_tree,
    reporting_tree_ids,
)
from tests.factories import EmployeeFactory, UserFactory


def ids(*employees):
    return {e.pk for e in employees}


def test_director_sees_indirect_reports_manager_only_own_tree(org):
    """T-27: a director's tree includes indirect reports; a manager sees only their own tree."""
    assert reporting_tree_ids(org.director) == ids(org.manager, org.dev1, org.dev2)
    assert reporting_tree_ids(org.manager) == ids(org.dev1, org.dev2)
    assert set(reporting_tree(org.ops_manager)) == {org.ops1}
    assert reporting_tree_ids(org.dev1) == set()
    everyone_else = set(Employee.objects.exclude(pk=org.ceo.pk).values_list("pk", flat=True))
    assert reporting_tree_ids(org.ceo) == everyone_else

    assert can_view(org.director, org.dev1)  # indirect report
    assert can_view(org.manager, org.dev2)
    assert not can_view(org.manager, org.ops1)  # another manager's tree
    assert not can_view(org.manager, org.director)  # never upwards


def test_reporting_tree_survives_a_cycle(org):
    """T-28: a reporting tree with a cycle in the data does not loop forever."""
    a, b, c = (EmployeeFactory() for _ in range(3))
    Employee.objects.filter(pk=b.pk).update(manager=a)
    Employee.objects.filter(pk=c.pk).update(manager=b)
    Employee.objects.filter(pk=a.pk).update(manager=c)  # a → b → c → a
    for person, others in ((a, (b, c)), (b, (a, c)), (c, (a, b))):
        assert reporting_tree_ids(person) == ids(*others)  # nobody is in their own tree

    Employee.objects.filter(pk=org.dev1.pk).update(manager=org.dev1)  # own manager
    assert reporting_tree_ids(Employee.objects.get(pk=org.dev1.pk)) == set()


def test_only_the_direct_manager_approves(org):
    """T-60: can_approve is true only for the direct manager; never self or a higher manager."""
    assert can_approve(org.manager, org.dev1)
    assert not can_approve(org.director, org.dev1)  # indirect: view only
    assert not can_approve(org.ceo, org.dev1)  # admin, but dev1 has a manager
    assert not can_approve(org.dev1, org.dev1)
    assert not can_approve(org.manager, org.manager)
    assert not can_approve(org.dev2, org.dev1)  # a peer
    assert not can_approve(org.dev1, org.manager)  # upwards


def test_admins_approve_only_employees_without_a_manager(org):
    """T-61: admins approve only employees with no manager, never themselves (CEO ← HR)."""
    assert org.ceo.manager is None
    assert can_approve(org.hr, org.ceo)
    assert not can_approve(org.ceo, org.ceo)
    assert not can_approve(org.hr, org.director)  # has a manager (the CEO)
    assert not can_approve(org.hr, org.hr)
    assert not can_approve(org.director, org.ceo)  # not an admin
    assert can_approve(org.ceo, org.hr)  # as HR's direct manager, not as admin


def test_can_view_and_can_edit(org):
    """Helper check: self and admins can view; editing is self or the approver."""
    assert can_view(org.dev1, org.dev1)
    assert not can_view(org.dev1, org.dev2)
    assert can_view(org.hr, org.dev1)  # admin sees everyone (B.3)
    assert can_edit(org.dev1, org.dev1)
    assert can_edit(org.manager, org.dev1)
    assert not can_edit(org.director, org.dev1)
    assert can_edit(org.hr, org.ceo)
    assert not can_edit(org.hr, org.dev1)


def test_roles_and_menu(org):
    """Helper check: manager is automatic; payroll flag only adds payroll (D-12)."""
    assert is_manager(org.manager) and is_manager(org.finance)
    assert not is_manager(org.dev1) and not is_manager(org.payroll)
    assert can_access_payroll(org.payroll) and can_access_payroll(org.hr)
    assert not can_access_payroll(org.manager)
    assert menu_for(org.dev1) == {
        "team": False,
        "approvals": False,
        "payroll": False,
        "admin": False,
    }
    assert menu_for(org.payroll) == {
        "team": False,
        "approvals": False,
        "payroll": True,
        "admin": False,
    }
    assert menu_for(org.manager) == {
        "team": True,
        "approvals": True,
        "payroll": False,
        "admin": False,
    }


@pytest.mark.django_db
def test_permission_mixin_for_class_views(org):
    """Helper check: PermissionRequiredMixin returns 403 when the check fails."""

    class PayrollOnly(PermissionRequiredMixin, View):
        permission_check = can_access_payroll

        def get(self, request):
            return HttpResponse("ok")

    request = RequestFactory().get("/x/")
    request.user = UserFactory(employee=org.payroll)
    assert PayrollOnly.as_view()(request).status_code == 200
    request.user = UserFactory(employee=org.dev1)
    with pytest.raises(PermissionDenied):
        PayrollOnly.as_view()(request)
