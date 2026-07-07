import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import decode_access_token, hash_reset_token, hash_password, verify_password
from app.models.user import PasswordResetToken, User
from app.schemas.auth import LoginRequest, PasswordResetConfirm, PasswordResetRequest, RegisterRequest
from app.services.auth import confirm_password_reset, login, register, request_password_reset
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAuthDb:
    def __init__(self, users=None, reset_tokens=None):
        self.users = list(users or [])
        self.reset_tokens = list(reset_tokens or [])
        self.added = []
        self.commits = 0
        self.rolled_back = False
        self.refreshed = []

    async def execute(self, statement, params=None):
        compiled = statement.compile()
        sql = str(compiled)
        bound = compiled.params

        if "lower(users.email)" in sql:
            expected = bound.get("lower_1", "")
            match = next((u for u in self.users if u.email.lower() == expected), None)
            return _FakeResult(match)

        if "password_reset_tokens.token_hash" in sql:
            expected = next(iter(bound.values()))
            match = next((t for t in self.reset_tokens if t.token_hash == expected), None)
            return _FakeResult(match)

        return _FakeResult(None)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, User):
            self.users.append(obj)
        if isinstance(obj, PasswordResetToken):
            self.reset_tokens.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        self.refreshed.append(obj)


def _settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        jwt_access_token_expire_minutes=60,
        login_max_attempts=5,
        login_lockout_minutes=15,
    )


def _register_request(email: str = "jan.kowalski@example.com") -> RegisterRequest:
    return RegisterRequest(
        email=email,
        password="StrongPass1",
        first_name="Jan",
        last_name="Kowalski",
        phone="+48 123 123 123",
    )


def _user(
    *,
    email: str = "jan.kowalski@example.com",
    password: str = "StrongPass1",
    failed_login_count: int = 0,
    locked_until=None,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        password_hash=hash_password(password),
        first_name="Jan",
        last_name="Kowalski",
        phone=None,
        is_active=True,
        failed_login_count=failed_login_count,
        locked_until=locked_until,
    )


def test_register_returns_jwt_and_user_id():
    db = _FakeAuthDb()
    settings = _settings()

    response = asyncio.run(register(db, _register_request(), settings))

    assert response.token_type == "bearer"
    assert response.expires_in == 3600
    assert response.user.user_id == db.users[0].id
    assert decode_access_token(response.access_token, settings) == db.users[0].id


def test_register_duplicate_email_raises_409():
    db = _FakeAuthDb(users=[_user(email="jan.kowalski@example.com")])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(register(db, _register_request(email="JAN.KOWALSKI@example.com"), _settings()))

    assert exc_info.value.status_code == 409


def test_login_with_valid_password_returns_jwt():
    user = _user(failed_login_count=2, locked_until=datetime.now(UTC) - timedelta(minutes=1))
    db = _FakeAuthDb(users=[user])
    settings = _settings()

    response = asyncio.run(
        login(db, LoginRequest(email=user.email, password="StrongPass1"), settings)
    )

    assert decode_access_token(response.access_token, settings) == user.id
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_login_with_locked_account_raises_423():
    user = _user(locked_until=datetime.now(UTC) + timedelta(minutes=5))
    db = _FakeAuthDb(users=[user])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(login(db, LoginRequest(email=user.email, password="StrongPass1"), _settings()))

    assert exc_info.value.status_code == 423


def test_login_with_five_bad_passwords_locks_account():
    user = _user(failed_login_count=4)
    db = _FakeAuthDb(users=[user])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            login(db, LoginRequest(email=user.email, password="WrongPass1"), _settings())
        )

    assert exc_info.value.status_code == 401
    assert user.failed_login_count == 5
    assert user.locked_until is not None


def test_confirm_password_reset_updates_hash_and_marks_token_used():
    user = _user(password="OldPass1")
    raw_token = "reset-token"
    reset_token = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        user=user,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        used_at=None,
    )
    db = _FakeAuthDb(users=[user], reset_tokens=[reset_token])

    response = asyncio.run(
        confirm_password_reset(
            db,
            PasswordResetConfirm(token=raw_token, new_password="NewStrongPass1"),
        )
    )

    assert response.message
    assert verify_password("NewStrongPass1", user.password_hash)
    assert reset_token.used_at is not None


def test_request_password_reset_returns_success_without_revealing_unknown_email():
    db = _FakeAuthDb()

    response = asyncio.run(
        request_password_reset(
            db,
            PasswordResetRequest(email="missing@example.com"),
            _settings(),
        )
    )

    assert response.message
    assert db.reset_tokens == []


def test_request_password_reset_stores_hashed_token_for_existing_user():
    user = _user()
    db = _FakeAuthDb(users=[user])

    response = asyncio.run(
        request_password_reset(db, PasswordResetRequest(email=user.email), _settings())
    )

    assert response.message
    assert len(db.reset_tokens) == 1
    assert db.reset_tokens[0].user_id == user.id
    assert db.reset_tokens[0].token_hash


def test_confirm_password_reset_rejects_expired_token():
    user = _user()
    raw_token = "expired-token"
    reset_token = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        user=user,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        used_at=None,
    )
    db = _FakeAuthDb(users=[user], reset_tokens=[reset_token])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            confirm_password_reset(
                db,
                PasswordResetConfirm(token=raw_token, new_password="NewStrongPass1"),
            )
        )

    assert exc_info.value.status_code == 400


def test_confirm_password_reset_rejects_used_token():
    user = _user()
    raw_token = "used-token"
    reset_token = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        user=user,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        used_at=datetime.now(UTC),
    )
    db = _FakeAuthDb(users=[user], reset_tokens=[reset_token])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            confirm_password_reset(
                db,
                PasswordResetConfirm(token=raw_token, new_password="NewStrongPass1"),
            )
        )

    assert exc_info.value.status_code == 400

