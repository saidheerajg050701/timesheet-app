import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from tests.factories import UserFactory


@pytest.mark.django_db
def test_password_is_hashed_with_argon2_never_plain_text():
    """T-06: stored password is an Argon2 hash, never the typed password."""
    user = UserFactory(password="Correct-Horse-42!")
    assert user.password.startswith("argon2")
    assert "Correct-Horse-42!" not in user.password
    assert user.check_password("Correct-Horse-42!")


@pytest.mark.django_db
def test_same_password_gives_different_hashes():
    """T-07: same password for two users gives different hashes (random salt)."""
    a = UserFactory(password="Same-Password-123")
    b = UserFactory(password="Same-Password-123")
    assert a.password != b.password


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Short-Pass1", "at least 12 characters"),  # 11 characters
        ("qwerty123456", "too common"),  # on Django's common-password list
        ("804719263518", "entirely numeric"),
    ],
)
def test_short_or_common_passwords_are_rejected(user, password, message):
    """T-08: password shorter than 12 characters or too common is rejected."""
    with pytest.raises(ValidationError) as exc:
        validate_password(password, user)
    assert any(message in m for m in exc.value.messages)


@pytest.mark.django_db
def test_twelve_character_password_is_accepted(user):
    """Helper check: the minimum length is exactly 12."""
    assert validate_password("Long-Enough1", user) is None
