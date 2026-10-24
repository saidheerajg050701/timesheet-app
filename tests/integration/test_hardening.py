import pytest
from django.test import Client
from django.views.defaults import server_error


@pytest.mark.django_db
def test_debug_off_serves_static_and_friendly_errors(settings, rf, user):
    """T-156: with DEBUG off, static files load, 404/500 pages show no code or settings (D-96)."""
    settings.DEBUG = False
    anonymous = Client()
    css = anonymous.get("/static/vendor/bootstrap/bootstrap.min.css")
    assert css.status_code == 200 and css["Content-Type"].startswith("text/css")
    assert anonymous.get("/static/vendor/htmx/htmx.min.js").status_code == 200
    assert anonymous.get("/static/no-such-file.js").status_code == 404

    browser = Client()
    browser.force_login(user)
    missing = browser.get("/no-such-page/")
    page = missing.content.decode()
    assert missing.status_code == 404 and 'id="not-found"' in page
    assert "Traceback" not in page and "SECRET_KEY" not in page and "urlpatterns" not in page

    crash = server_error(rf.get("/"))
    page = crash.content.decode()
    assert crash.status_code == 500 and 'id="server-error"' in page
    assert "Traceback" not in page and "SECRET_KEY" not in page
