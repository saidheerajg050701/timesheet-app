from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeRequiredMiddleware:
    """After an HR password reset, every page leads to Profile until a new one is chosen (D-91)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.must_change_password and not self.allowed(request):
            messages.warning(request, "Choose a new password before you continue.")
            return redirect("profile")
        return self.get_response(request)

    @staticmethod
    def allowed(request):
        return request.path in (reverse("profile"), reverse("logout")) or request.path.startswith(
            settings.STATIC_URL
        )
