import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_register_request_accepts_email_and_password_only():
    data = RegisterRequest(
        email="jan.kowalski@example.com",
        password="StrongPass1",
        password_confirm="StrongPass1",
    )

    assert data.email == "jan.kowalski@example.com"
    assert data.first_name is None
    assert data.last_name is None
    assert data.phone is None


def test_register_request_accepts_optional_profile_fields():
    data = RegisterRequest(
        email="jan.kowalski@example.com",
        password="StrongPass1",
        password_confirm="StrongPass1",
        first_name="Jan",
        last_name="Kowalski",
        phone="+48 500 600 700",
    )

    assert data.first_name == "Jan"


@pytest.mark.parametrize(
    "password",
    [
        "Short1",  # < 8
        "lowercase1",  # no uppercase
        "NO_DIGITS_HERE",  # no digit
    ],
)
def test_register_request_rejects_weak_password(password: str):
    with pytest.raises(ValidationError):
        RegisterRequest(email="jan.kowalski@example.com", password=password, password_confirm=password)


def test_register_request_rejects_mismatching_passwords():
    with pytest.raises(ValidationError, match="Passwords do not match"):
        RegisterRequest(
            email="jan.kowalski@example.com",
            password="StrongPass1",
            password_confirm="StrongPass2",
        )
