from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_password_hasher = PasswordHasher()


def constant_time_equals(left: str, right: str) -> bool:
    """Compare secrets without leaking timing information."""
    return compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def generate_secret(length_bytes: int = 32) -> str:
    return token_urlsafe(length_bytes)


def hash_password(plain: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when plain matches the Argon2id hash."""
    try:
        _password_hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    return True
