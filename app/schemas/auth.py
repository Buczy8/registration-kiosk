from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


_PASSWORD_MIN_LEN = 8
_PASSWORD_HAS_DIGIT_RE = re.compile(r"\d")
_PASSWORD_HAS_UPPER_RE = re.compile(r"[A-Z]")


def _validate_password_strength(value: str) -> str:
    if len(value) < _PASSWORD_MIN_LEN:
        raise ValueError("Password must be at least 8 characters long")
    if not _PASSWORD_HAS_DIGIT_RE.search(value):
        raise ValueError("Password must contain at least one digit")
    if not _PASSWORD_HAS_UPPER_RE.search(value):
        raise ValueError("Password must contain at least one uppercase letter")
    return value


def _validate_email(value: str) -> str:
    # Minimal validation without external dependency (email-validator).
    value = value.strip()
    if "@" not in value:
        raise ValueError("Invalid email address")
    local, _, domain = value.partition("@")
    if not local or "." not in domain:
        raise ValueError("Invalid email address")
    return value


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=_PASSWORD_MIN_LEN)
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class UserPublic(BaseModel):
    user_id: UUID
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class MessageResponse(BaseModel):
    message: str

