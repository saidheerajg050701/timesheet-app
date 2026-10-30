from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.contrib.staticfiles.views import serve as serve_static
from django.urls import include, path, re_path

from apps.directory.views import admin_login


@login_not_required
def static_file(request, path):
    """The vendored CSS/JS, also when DEBUG is off (D-96). Browsers must ask again on every page
    load (an unchanged file answers 304), so a new page never runs with yesterday's grid.js or
    theme.css from the browser cache (D-131)."""
    response = serve_static(request, path, insecure=True)
    response["Cache-Control"] = "no-cache"
    return response


urlpatterns = [
    path("admin/login/", admin_login),  # one login page for the whole app
    path("admin/", admin.site.urls),
    path("", include("apps.directory.urls")),
    path("", include("apps.timesheets.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.payroll.urls")),
    # The vendored CSS/JS also when DEBUG is off: fine for a local single-machine app (D-96).
    re_path(r"^static/(?P<path>.*)$", static_file),
]
