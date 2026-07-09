from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

import jwt
from datetime import datetime, timedelta, UTC
from uuid import UUID
from app.core.config import Settings
import secrets

__all__ = [
    "constant_time_equals",
    "sha256_hex",
    "generate_secret",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_reset_token",
    "hash_reset_token",
]

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
)


def constant_time_equals(left: str, right: str) -> bool:
    """Compare secrets without leaking timing information."""
    return compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def generate_secret(length_bytes: int = 32) -> str:
    return secrets.token_urlsafe(length_bytes)


def hash_password(plain: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when plain matches the Argon2id hash."""
    try:
        _password_hasher.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False
    return True


def create_access_token(user_id: UUID, settings: Settings) -> str:
    """
    Tworzy token JWT dla podanego user_id, korzystając z konfiguracji aplikacji.
    """
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode = {"sub": str(user_id), "exp": expire}

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

def decode_access_token(token: str, settings: Settings) -> UUID:
    """
    Dekoduje token JWT i zwraca identyfikator użytkownika jako UUID.
    Rzuca wyjątki jwt.InvalidTokenError lub jwt.ExpiredSignatureError w przypadku błędu.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id_str = payload.get("sub")

        if not user_id_str:
            raise jwt.InvalidTokenError("Brak pola 'sub' w tokenie")

        return UUID(user_id_str)

    except ValueError as e:
        raise jwt.InvalidTokenError("Nieprawidłowy format UUID w tokenie") from e

def generate_reset_token() -> str:
    """
    Generuje token do resetowania hasła.
    Działa jako semantyczny wrapper/alias na generate_secret().
    """
    return generate_secret()

def hash_reset_token(token: str) -> str:
    """
    Haszuje token resetowania hasła przed zapisem do bazy danych.
    Dzięki temu, nawet w przypadku wycieku bazy, atakujący nie pozna surowych tokenów.
    """
    return sha256_hex(token)