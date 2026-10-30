from django.contrib.staticfiles import finders


def test_home_dashboard_renders_with_vendored_assets(client, user):
    """Helper check: / renders the dashboard using the offline vendor files (incl. Chart.js)."""
    client.force_login(user)
    response = client.get("/")
    assert response.status_code == 200
    html = response.content.decode()
    assert '<h1 class="h3 mb-0">Dashboard</h1>' in html and user.employee.employee_code in html
    for asset in (
        "vendor/bootstrap/bootstrap.min.css",
        "vendor/htmx/htmx.min.js",
        "vendor/chartjs/chart.umd.min.js",
        "analytics/dashboard.js",
    ):
        assert asset in html
        assert finders.find(asset)
