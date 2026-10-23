from django.urls import path

from payroll import views

urlpatterns = [
    path("payroll/", views.payroll_home, name="payroll"),
]
