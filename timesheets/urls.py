from django.urls import path

from timesheets import views

urlpatterns = [
    path("timesheets/", views.timesheet_list, name="timesheets"),
    path("requests/", views.request_list, name="requests"),
    path("approvals/", views.approval_list, name="approvals"),
]
