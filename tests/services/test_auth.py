import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import decode_access_token, hash_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
import app.services.auth as auth_service
from app.services.auth import login, register
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAuthDb:
    def __init__(self, users=None):
        self.users = list(users or [])
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

        return _FakeResult(None)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, User):
            self.users.append(obj)

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


class _ExpiringUser:
    def __init__(self, user_id, email: str, password_hash_value: str):
        self._id = user_id
        self._email = email
        self.password_hash = password_hash_value
        self.failed_login_count = 0
        self.locked_until = None
        self._expired = False

    @property
    def id(self):
        if self._expired:
            raise RuntimeError("expired user.id access")
        return self._id

    @property
    def email(self):
        if self._expired:
            raise RuntimeError("expired user.email access")
        return self._email

    def expire(self):
        self._expired = True


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




def test_login_does_not_access_user_attributes_after_reset_commit(monkeypatch):
    user_id = uuid4()
    user = _ExpiringUser(user_id, "jan.kowalski@example.com", hash_password("StrongPass1"))

    async def _fake_get_user_by_email(db, email):
        return user

    async def _fake_reset_failed_login(db, u):
        u.expire()

    monkeypatch.setattr(auth_service, "get_user_by_email", _fake_get_user_by_email)
    monkeypatch.setattr(auth_service, "is_account_locked", lambda _: False)
    monkeypatch.setattr(auth_service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth_service, "reset_failed_login", _fake_reset_failed_login)

    response = asyncio.run(
        auth_service.login(
            db=object(),
            data=LoginRequest(email="jan.kowalski@example.com", password="StrongPass1"),
            settings=_settings(),
        )
    )

    assert decode_access_token(response.access_token, _settings()) == user_id



