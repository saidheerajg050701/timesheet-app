from django.contrib.staticfiles import finders


def test_home_placeholder_renders_with_vendored_assets(client):
    """Helper check: / renders the placeholder page using the offline vendor files."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.content.decode()
    assert "Employee Timesheets" in html
    for asset in ("vendor/bootstrap/bootstrap.min.css", "vendor/htmx/htmx.min.js"):
        assert asset in html
        assert finders.find(asset)
    assert finders.find("vendor/chartjs/chart.umd.min.js")
