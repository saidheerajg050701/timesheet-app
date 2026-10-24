from django.urls import path

from payroll import views

urlpatterns = [
    path("payroll/", views.payroll_home, name="payroll"),
    path("payroll/export/", views.payroll_export, name="payroll_export"),
    path("payroll/batches/<str:batch>.csv", views.payroll_batch_csv, name="payroll_batch_csv"),
    path("payroll/batches/<str:batch>/paid/", views.payroll_mark_paid, name="payroll_mark_paid"),
    path("payroll/corrections/", views.payroll_corrections, name="payroll_corrections"),
]
