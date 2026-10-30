"""The admin site: directory admins only, nothing outside the audited services (D-87, D-93)."""

from functools import update_wrapper

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.directory.admin_base import ViewOnlyAdmin


class CompanyAdminSite(admin.AdminSite):
    site_header = "Timesheets Admin"  # light branding only (D-104)
    site_title = "Timesheets Admin"

    def has_permission(self, request):
        """Only a logged-in, ACTIVE employee with is_admin (is_staff mirrors it, D-13)."""
        user = request.user
        employee = getattr(user, "employee", None) if user.is_authenticated else None
        return bool(
            user.is_active
            and user.is_staff
            and employee is not None
            and employee.is_admin
            and employee.status == employee.Status.ACTIVE
        )

    def admin_view(self, view, cacheable=False):
        """Logged-in non-admins get 403 straight away; anonymous users go to /login/ (D-29)."""
        inner = super().admin_view(view, cacheable)

        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and not self.has_permission(request):
                raise PermissionDenied("Only directory admins can open the admin site.")
            return inner(request, *args, **kwargs)

        return update_wrapper(wrapper, inner)

    def password_change(self, request, extra_context=None):
        """Passwords change only on Profile, where the change is audited (D-91)."""
        return redirect("profile")

    def password_change_done(self, request, extra_context=None):
        return redirect("profile")


class CompanyAdminConfig(AdminConfig):
    default_site = "apps.directory.admin_site.CompanyAdminSite"

    def ready(self):
        from django.contrib.auth.models import Group  # models load after the app configs

        super().ready()  # every app's admin.py is registered now
        site = admin.site
        if site.is_registered(Group):  # access comes from is_admin, not groups (D-13)
            site.unregister(Group)
        for model in apps.get_app_config("axes").get_models():  # lockouts: view only (D-87)
            if site.is_registered(model):
                original = type(site.get_model_admin(model))
                site.unregister(model)
                site.register(
                    model, type(f"ViewOnly{original.__name__}", (ViewOnlyAdmin, original), {})
                )
