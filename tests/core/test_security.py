from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    constant_time_equals,
    create_access_token,
    decode_access_token,
    generate_secret,
    hash_password,
    sha256_hex,
    verify_password,
)
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN


def test_hash_password_and_verify_password_accepts_correct_password():
    hashed = hash_password("StrongPass123!")

    assert hashed != "StrongPass123!"
    assert hashed.startswith("$argon2")
    assert verify_password("StrongPass123!", hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("StrongPass123!")

    assert verify_password("WrongPass123!", hashed) is False


def test_constant_time_equals_compares_strings():
    assert constant_time_equals("same-token", "same-token")
    assert not constant_time_equals("same-token", "other-token")


def test_sha256_hex_hashes_payload():
    assert sha256_hex("payload") == (
        "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"
    )


def test_generate_secret_returns_sufficient_length():
    assert len(generate_secret()) >= 32


def _jwt_settings(*, secret: str = TEST_JWT_SECRET) -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=secret,
    )


def test_jwt_encode_decode_roundtrip():
    user_id = uuid4()
    settings = _jwt_settings()

    token = create_access_token(user_id, settings)
    decoded_user_id = decode_access_token(token, settings)

    assert decoded_user_id == user_id


def test_expired_jwt_is_rejected():
    settings = _jwt_settings()
    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token, settings)


def test_jwt_signed_with_different_secret_is_rejected():
    valid_settings = _jwt_settings()
    foreign_settings = _jwt_settings(secret="another-jwt-secret-key-min-32-chars")
    token = create_access_token(uuid4(), foreign_settings)

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, valid_settings)


def test_jwt_with_tampered_sub_is_rejected():
    settings = _jwt_settings()
    token = create_access_token(uuid4(), settings)
    header_b64, _payload_b64, signature_b64 = token.split(".")
    tampered_payload = urlsafe_b64encode(b'{"sub":"tampered","exp":9999999999}').decode(
        "ascii"
    ).rstrip("=")
    tampered_token = f"{header_b64}.{tampered_payload}.{signature_b64}"

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered_token, settings)
