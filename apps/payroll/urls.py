from django.urls import path

from apps.payroll import views

urlpatterns = [
    path("payroll/", views.payroll_home, name="payroll"),
    path("payroll/periods/<isodate:period>/", views.payroll_period, name="payroll_period"),
    path(
        "payroll/periods/<isodate:period>/finalize/",
        views.payroll_finalize,
        name="payroll_finalize",
    ),
    path(
        "payroll/periods/<isodate:period>/paid/",
        views.payroll_register_paid,
        name="payroll_register_paid",
    ),
    path(
        "payroll/periods/<isodate:period>/register.csv",
        views.payroll_register_csv,
        name="payroll_register_csv",
    ),
    path(
        "payroll/periods/<isodate:period>/detail.csv",
        views.payroll_detail_csv,
        name="payroll_detail_csv",
    ),
    path("payroll/registers.csv", views.payroll_registers_csv, name="payroll_registers_csv"),
    path("payroll/pending/", views.payroll_pending, name="payroll_pending"),
    path("payroll/pending.csv", views.payroll_pending_csv, name="payroll_pending_csv"),
    path("payroll/batches/<str:batch>.csv", views.payroll_batch_csv, name="payroll_batch_csv"),
    path("payroll/corrections/", views.payroll_corrections, name="payroll_corrections"),
]
