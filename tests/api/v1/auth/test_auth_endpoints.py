from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.core.security import decode_access_token, hash_password
from app.db.session import get_db
from app.models.user import User
from main import app
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
        return None

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


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_settings] = lambda: _settings()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)


def _register_payload(email: str = "jan.kowalski@example.com") -> dict:
    return {
        "email": email,
        "password": "StrongPass1",
        "password_confirm": "StrongPass1",
    }


def _login_payload(email: str = "jan.kowalski@example.com", password: str = "StrongPass1") -> dict:
    return {"email": email, "password": password}


def _user(*, email: str = "jan.kowalski@example.com", password: str = "StrongPass1", locked=False) -> User:
    return User(
        id=uuid4(),
        email=email,
        password_hash=hash_password(password),
        first_name="Jan",
        last_name="Kowalski",
        phone=None,
        is_active=True,
        failed_login_count=0,
        locked_until=(datetime.now(UTC) + timedelta(minutes=5)) if locked else None,
    )


def test_register_without_kiosk_token_returns_401(client: TestClient):
    response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 401


def test_register_ok_returns_201_and_jwt(client: TestClient):
    db = _FakeAuthDb()
    app.dependency_overrides[get_db] = lambda: db

    response = client.post(
        "/api/v1/auth/register",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_register_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["access_token"]
    assert payload["user"]["user_id"]
    assert decode_access_token(payload["access_token"], _settings())


def test_register_duplicate_returns_409(client: TestClient):
    db = _FakeAuthDb(users=[_user(email="jan.kowalski@example.com")])
    app.dependency_overrides[get_db] = lambda: db

    response = client.post(
        "/api/v1/auth/register",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_register_payload(email="JAN.KOWALSKI@example.com"),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_login_ok_returns_200_and_jwt(client: TestClient):
    user = _user()
    db = _FakeAuthDb(users=[user])
    app.dependency_overrides[get_db] = lambda: db

    response = client.post(
        "/api/v1/auth/login",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_login_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert decode_access_token(payload["access_token"], _settings()) == user.id


def test_login_wrong_password_returns_401(client: TestClient):
    db = _FakeAuthDb(users=[_user()])
    app.dependency_overrides[get_db] = lambda: db

    response = client.post(
        "/api/v1/auth/login",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_login_payload(password="WrongPass1"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_locked_returns_423(client: TestClient):
    db = _FakeAuthDb(users=[_user(locked=True)])
    app.dependency_overrides[get_db] = lambda: db

    response = client.post(
        "/api/v1/auth/login",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_login_payload(),
    )

    assert response.status_code == 423
    assert response.json()["error"]["code"] == "locked"



