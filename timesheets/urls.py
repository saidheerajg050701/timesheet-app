from datetime import date

from django.urls import path, register_converter

from timesheets import views


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
    path("requests/", views.request_list, name="requests"),
    path("approvals/", views.approval_list, name="approvals"),
]
