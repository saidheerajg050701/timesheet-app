from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse

from directory.forms import LoginForm, SignupForm
from directory.services.signup import create_account


class LoginView(auth_views.LoginView):
    form_class = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have been logged out.")
        return response


@login_not_required
def admin_login(request):
    """Send /admin/login/ to the one app login page; logged-in non-admins get 403."""
    if request.user.is_authenticated:
        raise PermissionDenied("Only directory admins can open the admin site.")
    return redirect_to_login(request.GET.get("next") or reverse("admin:index"))


@login_not_required
def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, refused = create_account(form.eligibility, form.cleaned_data["password1"])
        if refused:
            form.add_error("email", refused.message)
        else:
            login(request, user, backend="directory.backends.EmployeeBackend")
            messages.success(
                request, f"Welcome, {user.employee.first_name}! Your account is ready."
            )
            return redirect("home")
    return render(request, "registration/signup.html", {"form": form})
