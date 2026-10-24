from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.contrib.staticfiles.views import serve as serve_static
from django.urls import include, path, re_path

from directory.views import admin_login

urlpatterns = [
    path("admin/login/", admin_login),  # one login page for the whole app
    path("admin/", admin.site.urls),
    path("", include("directory.urls")),
    path("", include("timesheets.urls")),
    path("", include("analytics.urls")),
    path("", include("payroll.urls")),
    # The vendored CSS/JS also when DEBUG is off: fine for a local single-machine app (D-96).
    re_path(r"^static/(?P<path>.*)$", login_not_required(serve_static), {"insecure": True}),
]
