"""Login helpers (FR-1)."""

from apps.directory.services.signup import normalize_email


def lockout_username(request, credentials):
    """The account key django-axes counts failures against (D-28).

    Lower-cased and trimmed, so "DEV2@…" and "dev2@…" share one lockout.
    """
    username = (credentials or {}).get("username") or request.POST.get("username", "")
    return normalize_email(username)
