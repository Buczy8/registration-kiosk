import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_register_request_accepts_strong_password():
    data = RegisterRequest(
        email="jan.kowalski@example.com",
        password="StrongPass1",
        first_name="Jan",
        last_name="Kowalski",
        phone="+48 500 600 700",
    )

    assert data.email == "jan.kowalski@example.com"


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
        RegisterRequest(email="jan.kowalski@example.com", password=password)

