from types import SimpleNamespace

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from analytics.services.metrics import Overtime, Punctuality
from analytics.services.team import sort_people, utilization
from directory.services.permissions import reporting_tree_ids, team_scope


def person(last, worked, available, late=0):
    return SimpleNamespace(
        employee=SimpleNamespace(first_name="A", last_name=last),
        worked=worked,
        utilization=utilization(worked, available),
        punctuality=Punctuality(on_time=1, late=late),
        overtime=Overtime(),
        pending=0,
    )


def test_utilization_rounds_and_handles_nothing_available():
    """Helper check: whole percent; None when nothing was available (D-82)."""
    assert utilization(1200, 2400) == 50
    assert utilization(2600, 2400) == 108  # over 100% is shown as is
    assert utilization(0, 0) is None and utilization(60, 0) is None


def test_sorting_by_any_column():
    """Helper check: server-side sort, ties by name, empty utilization sorts lowest (D-84)."""
    people = [
        person("Cole", 600, 0),
        person("Adams", 600, 2400, late=2),
        person("Baker", 1200, 2400),
    ]
    names = lambda rows: [p.employee.last_name for p in rows]  # noqa: E731
    assert names(sort_people(people, "name", "asc")) == ["Adams", "Baker", "Cole"]
    assert names(sort_people(people, "worked", "desc")) == ["Baker", "Adams", "Cole"]
    assert names(sort_people(people, "worked", "asc")) == ["Adams", "Cole", "Baker"]  # tie by name
    assert names(sort_people(people, "utilization", "desc")) == ["Baker", "Adams", "Cole"]
    assert names(sort_people(people, "late", "desc")) == ["Adams", "Baker", "Cole"]
    assert names(sort_people(people, "nonsense", "asc")) == ["Adams", "Baker", "Cole"]


@pytest.mark.django_db
def test_reporting_tree_is_one_query(org):
    """Helper check: the tree is built in memory from one query, however deep it is (D-86)."""
    with CaptureQueriesContext(connection) as queries:
        tree = reporting_tree_ids(org.ceo)
    assert len(queries) == 1 and org.dev1.pk in tree
    with CaptureQueriesContext(connection) as queries:
        assert team_scope(org.director, "direct") == {org.manager.pk}
    assert len(queries) == 1
