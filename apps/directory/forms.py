from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import (
    password_validators_help_text_html,
    validate_password,
)
from django.core.exceptions import ValidationError

from apps.directory.services.signup import check_signup_eligibility, normalize_email


class BootstrapFormMixin:
    """Bootstrap classes on every input, plus is-invalid on fields with errors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["class"] = "form-control is-invalid"


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        # Same text for every failure: never reveal whether an account exists or is inactive.
        "invalid_login": "Wrong email or password.",
        "inactive": "Wrong email or password.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget.attrs.update(autocomplete="email", autofocus=True)

    def clean_username(self):
        return normalize_email(self.cleaned_data["username"])


class SignupForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    eligibility = None

    def clean_email(self):
        self.eligibility = check_signup_eligibility(self.cleaned_data["email"])
        if not self.eligibility.ok:
            raise ValidationError(self.eligibility.message, code=self.eligibility.refusal.lower())
        return self.eligibility.email

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get("password1"), cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords don't match.")
        elif password1 and self.eligibility and self.eligibility.ok:
            employee = self.eligibility.employee
            candidate = get_user_model()(
                email=self.eligibility.email,
                employee=employee,
                first_name=employee.first_name,
                last_name=employee.last_name,
            )
            try:
                validate_password(password1, candidate)  # FR-2 step 5
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


class ProfilePasswordForm(BootstrapFormMixin, PasswordChangeForm):
    """Current password + new password twice; the validators apply (12+ characters, FR-2)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Current password"
        self.fields["new_password1"].label = "New password"
        self.fields["new_password2"].label = "Confirm new password"
        self.fields["old_password"].widget.attrs.pop("autofocus", None)


IMPORT_MAX_BYTES = 1024 * 1024  # 1 MB (D-92)


class ImportForm(forms.Form):
    file = forms.FileField(label="CSV file", help_text="Same columns as Export CSV. Max 1 MB.")

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > IMPORT_MAX_BYTES:
            raise ValidationError("The file is larger than 1 MB.")
        try:
            return upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValidationError("Save the file as CSV UTF-8 and try again.") from None
