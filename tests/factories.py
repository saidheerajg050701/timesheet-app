"""factory_boy factories (B.11)."""

from datetime import date, time

import factory
import factory.random
from django.conf import settings
from factory.django import DjangoModelFactory

from directory.models import Employee, Team, User
from timesheets.models import Project, TimeEntry, Timesheet

TEST_PASSWORD = "Test-Password-123!"

factory.random.reseed_random("timesheet-app-tests")  # repeatable Faker values


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Team {n}")
    department = "Technology"


class EmployeeFactory(DjangoModelFactory):
    class Meta:
        model = Employee

    employee_code = factory.Sequence(lambda n: f"EMP-{9000 + n:04d}")
    email = factory.Sequence(lambda n: f"person{n}{settings.COMPANY_EMAIL_DOMAIN}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    job_title = "Software Engineer"
    team = factory.SubFactory(TeamFactory)
    location = "Dallas"
    hire_date = date(2024, 1, 8)


class UserFactory(DjangoModelFactory):
    """Login account; goes through UserManager.create_user so the password is hashed."""

    class Meta:
        model = User

    employee = factory.SubFactory(EmployeeFactory)
    password = TEST_PASSWORD

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return cls._get_manager(model_class).create_user(*args, **kwargs)


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    code = factory.Sequence(lambda n: f"PRJ-{900 + n}")
    name = factory.Sequence(lambda n: f"Project {n}")


class TimesheetFactory(DjangoModelFactory):
    class Meta:
        model = Timesheet

    employee = factory.SubFactory(EmployeeFactory)
    week_start = date(2026, 10, 18)  # a Sunday (D-111)


class TimeEntryFactory(DjangoModelFactory):
    class Meta:
        model = TimeEntry

    timesheet = factory.SubFactory(TimesheetFactory)
    work_date = factory.LazyAttribute(lambda o: o.timesheet.week_start)
    category = TimeEntry.Category.PROJECT
    project = factory.SubFactory(ProjectFactory)
    start_time = time(9, 0)
    end_time = time(17, 0)
    minutes = 480
    reason = "Feature development"
