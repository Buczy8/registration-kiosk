from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User, UserProfile
from main import app
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeMeDb:
    def __init__(self, *, users=None, profiles=None):
        self.users = list(users or [])
        self.profiles = list(profiles or [])
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, statement, params=None):
        compiled = statement.compile()
        sql = str(compiled)
        expected_id = next(iter(compiled.params.values()), None)

        if "FROM users" in sql:
            user = next((u for u in self.users if str(u.id) == str(expected_id)), None)
            return _FakeResult(user)

        if "FROM user_profiles" in sql:
            profile = next(
                (p for p in self.profiles if str(p.user_id) == str(expected_id)),
                None,
            )
            return _FakeResult(profile)

        return _FakeResult(None)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, UserProfile):
            self.profiles.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


def _settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_settings] = lambda: _settings()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)


def _user() -> User:
    return User(
        id=uuid4(),
        email="jan.kowalski@example.com",
        password_hash="hash",
        first_name="Jan",
        last_name="Kowalski",
        phone="+48 500 600 700",
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )


def _profile(user_id, *, vehicles_json=None, **overrides) -> UserProfile:
    profile = UserProfile(
        user_id=user_id,
        address="Warszawa",
        birth_date=date(1990, 1, 1),
        document_number="ABC123",
        ice_name="Anna",
        ice_phone="+48 700 800 900",
        vehicles_json=vehicles_json or {},
    )
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


def _auth_headers(*, with_kiosk=True, with_bearer=False, user_id=None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if with_kiosk:
        headers[KIOSK_TOKEN_HEADER] = TEST_KIOSK_TOKEN
    if with_bearer and user_id is not None:
        token = create_access_token(user_id, _settings())
        headers["Authorization"] = f"Bearer {token}"
    return headers


def test_get_me_profile_without_jwt_returns_401(client: TestClient):
    response = client.get("/api/v1/me/profile", headers=_auth_headers(with_kiosk=True))
    assert response.status_code == 401


def test_get_me_profile_without_kiosk_token_returns_401(client: TestClient):
    user = _user()
    db = _FakeMeDb(users=[user], profiles=[_profile(user.id)])
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/profile",
        headers=_auth_headers(with_kiosk=False, with_bearer=True, user_id=user.id),
    )
    assert response.status_code == 401


def test_get_me_profile_with_jwt_and_empty_profile_returns_200(client: TestClient):
    user = _user()
    db = _FakeMeDb(users=[user], profiles=[])
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/profile",
        headers=_auth_headers(with_kiosk=True, with_bearer=True, user_id=user.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == user.email
    assert payload["vehicles_json"] == {}


def test_get_me_profile_with_data_returns_vehicles_in_response(client: TestClient):
    user = _user()
    db = _FakeMeDb(
        users=[user],
        profiles=[
            _profile(
                user.id,
                vehicles_json={
                    "car": {
                        "brand_model": "BMW M3",
                        "registration_number": "WX 12345",
                    }
                },
            )
        ],
    )
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/profile",
        headers=_auth_headers(with_kiosk=True, with_bearer=True, user_id=user.id),
    )

    assert response.status_code == 200
    vehicles = response.json()["vehicles_json"]
    assert vehicles["car"]["brand_model"] == "BMW M3"
    assert vehicles["car"]["registration_number"] == "WX 12345"


def test_get_me_form_prefill_driver_car_returns_vehicle_from_profile(client: TestClient):
    user = _user()
    db = _FakeMeDb(
        users=[user],
        profiles=[
            _profile(
                user.id,
                pesel="12345678901",
                ice_name="Anna Kowalska",
                ice_phone="+48 700 800 900",
                vehicles_json={
                    "car": {
                        "brand_model": "BMW M3",
                        "registration_number": "WX 12345",
                    }
                },
            )
        ],
    )
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/form-prefill?role=driver&vehicle_type=car",
        headers=_auth_headers(with_kiosk=True, with_bearer=True, user_id=user.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["participant_role"] == "driver"
    assert payload["vehicle_type"] == "car"
    assert payload["vehicle"]["brand_model"] == "BMW M3"
    assert payload["pesel"] == "12345678901"
    assert payload["ice_name"] == "Anna Kowalska"


def test_get_me_profile_returns_last_role_and_vehicle(client: TestClient):
    user = _user()
    profile = _profile(user.id)
    profile.last_participant_role = "driver"
    profile.last_vehicle_type = "car"
    db = _FakeMeDb(users=[user], profiles=[profile])
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/profile",
        headers=_auth_headers(with_kiosk=True, with_bearer=True, user_id=user.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_participant_role"] == "driver"
    assert payload["last_vehicle_type"] == "car"


def test_get_me_form_prefill_without_query_returns_422(client: TestClient):
    user = _user()
    db = _FakeMeDb(users=[user], profiles=[_profile(user.id)])
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/form-prefill",
        headers=_auth_headers(with_kiosk=True, with_bearer=True, user_id=user.id),
    )
    assert response.status_code == 422


def test_get_me_form_prefill_legal_guardian_returns_minimal_response(client: TestClient):
    user = _user()
    db = _FakeMeDb(users=[user], profiles=[_profile(user.id)])
    app.dependency_overrides[get_db] = lambda: db

    response = client.get(
        "/api/v1/me/form-prefill?role=legal_guardian&vehicle_type=car",
        headers=_auth_headers(with_kiosk=True, with_bearer=True, user_id=user.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["participant_role"] == "legal_guardian"
    assert payload["address"] == "Warszawa"
    assert payload["ice_name"] == "Anna"
