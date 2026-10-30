from datetime import date

from django.urls import path, register_converter

from timesheets.views import approvals, requests, weeks


class IsoDateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value):
        return date.fromisoformat(value)  # ValueError → no match → 404

    def to_url(self, value):
        return value.isoformat()


register_converter(IsoDateConverter, "isodate")

urlpatterns = [
    path("timesheets/", weeks.timesheet_list, name="timesheets"),
    path("timesheets/<isodate:week>/", weeks.timesheet_week, name="timesheet_week"),
    path("timesheets/<isodate:week>/totals/", weeks.timesheet_totals, name="timesheet_totals"),
    path("timesheets/<isodate:week>/row/", weeks.timesheet_row, name="timesheet_row"),
    path("timesheets/<isodate:week>/rows/", weeks.timesheet_rows, name="timesheet_rows"),
    path(
        "timesheets/<isodate:week>/projects/", weeks.timesheet_projects, name="timesheet_projects"
    ),
    path(
        "timesheets/<isodate:week>/request-change/",
        weeks.request_change,
        name="request_change",
    ),
    path("requests/", weeks.request_list, name="requests"),
    path("approvals/", approvals.approval_list, name="approvals"),
    path("approvals/bulk/", approvals.approval_bulk, name="approval_bulk"),
    path(
        "approvals/<isodate:period>/<str:employee_code>/",
        approvals.approval_detail,
        name="approval_detail",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/edit/",
        approvals.approval_week_edit,
        name="approval_week_edit",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/rows/",
        approvals.approval_week_rows,
        name="approval_week_rows",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/projects/",
        approvals.approval_week_projects,
        name="approval_week_projects",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/totals/",
        approvals.approval_week_totals,
        name="approval_week_totals",
    ),
    path("approvals/requests/", requests.request_inbox, name="request_inbox"),
    path("approvals/requests/<int:pk>/", requests.request_detail, name="request_detail"),
    path("approvals/requests/<int:pk>/edit/", requests.request_edit, name="request_edit"),
    path("approvals/requests/<int:pk>/rows/", requests.request_rows, name="request_rows"),
    path(
        "approvals/requests/<int:pk>/projects/",
        requests.request_projects,
        name="request_projects",
    ),
    path(
        "approvals/requests/<int:pk>/totals/",
        requests.request_totals,
        name="request_totals",
    ),
]
