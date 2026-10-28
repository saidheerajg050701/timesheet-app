from datetime import date

from django.urls import path, register_converter

from timesheets import approval_views, request_views, views


class IsoDateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value):
        return date.fromisoformat(value)  # ValueError → no match → 404

    def to_url(self, value):
        return value.isoformat()


register_converter(IsoDateConverter, "isodate")

urlpatterns = [
    path("timesheets/", views.timesheet_list, name="timesheets"),
    path("timesheets/<isodate:week>/", views.timesheet_week, name="timesheet_week"),
    path("timesheets/<isodate:week>/totals/", views.timesheet_totals, name="timesheet_totals"),
    path("timesheets/<isodate:week>/row/", views.timesheet_row, name="timesheet_row"),
    path("timesheets/<isodate:week>/rows/", views.timesheet_rows, name="timesheet_rows"),
    path(
        "timesheets/<isodate:week>/projects/", views.timesheet_projects, name="timesheet_projects"
    ),
    path(
        "timesheets/<isodate:week>/request-change/",
        views.request_change,
        name="request_change",
    ),
    path("requests/", views.request_list, name="requests"),
    path("approvals/", approval_views.approval_list, name="approvals"),
    path("approvals/bulk/", approval_views.approval_bulk, name="approval_bulk"),
    path(
        "approvals/<isodate:period>/<str:employee_code>/",
        approval_views.approval_detail,
        name="approval_detail",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/edit/",
        approval_views.approval_week_edit,
        name="approval_week_edit",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/rows/",
        approval_views.approval_week_rows,
        name="approval_week_rows",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/projects/",
        approval_views.approval_week_projects,
        name="approval_week_projects",
    ),
    path(
        "approvals/<isodate:period>/<str:employee_code>/weeks/<isodate:week>/totals/",
        approval_views.approval_week_totals,
        name="approval_week_totals",
    ),
    path("approvals/requests/", request_views.request_inbox, name="request_inbox"),
    path("approvals/requests/<int:pk>/", request_views.request_detail, name="request_detail"),
    path("approvals/requests/<int:pk>/edit/", request_views.request_edit, name="request_edit"),
    path("approvals/requests/<int:pk>/rows/", request_views.request_rows, name="request_rows"),
    path(
        "approvals/requests/<int:pk>/projects/",
        request_views.request_projects,
        name="request_projects",
    ),
    path(
        "approvals/requests/<int:pk>/totals/",
        request_views.request_totals,
        name="request_totals",
    ),
]
