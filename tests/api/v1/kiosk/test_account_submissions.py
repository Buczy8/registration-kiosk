import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.core.deps import KIOSK_TOKEN_HEADER
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.form import Form
from app.models.submission import Submission
from app.models.user import User, UserProfile
from main import app
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN
from tests.fakes.async_db import async_get_db_override
from tests.fixtures.signature_samples import sample_signature_base64


def _form() -> Form:
    return Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json={
            "required": ["first_name", "last_name"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
            },
        },
        pdf_template_path="templates/forms/guest-registration-v1.pdf",
        is_active=True,
    )


def _user() -> User:
    return User(
        id=uuid.uuid4(),
        email="jan.kowalski@example.com",
        password_hash="hash",
        first_name=None,
        last_name=None,
        phone=None,
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _FakeDualDb:
    def __init__(self, form: Form, *, start_number: int = 42, user: User | None = None,
                 profile: UserProfile | None = None):
        self.form = form
        self.start_number = start_number
        self.user = user
        self.profile = profile
        self.added: list = []
        self.committed = False
        self.rolled_back = False
        self._submission: Submission | None = None

    async def execute(self, statement, params=None):
        sql = str(statement)
        if "next_start_number" in sql:
            return _FakeResult(self.start_number)
        if "FROM users" in sql:
            return _FakeResult(self.user)
        if "user_profiles" in sql:
            return _FakeResult(self.profile)
        return _FakeResult(self.form)

    def add(self, obj) -> None:
        self.added.append(obj)
        if isinstance(obj, UserProfile):
            self.profile = obj
        elif isinstance(obj, Submission):
            self._submission = obj

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, obj) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()


def _payload(**overrides) -> dict:
    return {
        "participant_role": "driver",
        "vehicle_type": "car",
        "payload_json": {
            "first_name": "Jan",
            "last_name": "Kowalski",
            "vehicle_brand_model": "BMW M3",
            "vehicle_registration_number": "WX 12345",
        },
        "consents_json": {"terms": True},
        "declarations_accepted": True,
        "signature_image_base64": sample_signature_base64(),
        **overrides,
    }


def _bearer(user: User) -> dict:
    token = create_access_token(user.id, _settings())
    return {"Authorization": f"Bearer {token}"}


def _settings():
    from app.core.config import Settings

    return Settings(kiosk_token=TEST_KIOSK_TOKEN, jwt_secret_key=TEST_JWT_SECRET)


def test_account_submission_requires_kiosk_token(client_with_storage: TestClient):
    user = _user()
    response = client_with_storage.post(
        "/api/v1/kiosk/submissions",
        headers=_bearer(user),
        json=_payload(),
    )
    assert response.status_code == 401


def test_account_submission_sets_account_mode_and_user_id(client_with_storage: TestClient):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeDualDb(_form(), start_number=55, user=user, profile=profile)
    app.dependency_overrides[get_db] = async_get_db_override(db)

    response = client_with_storage.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN, **_bearer(user)},
        json=_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["mode"] == "account"
    assert payload["start_number"] == 55
    assert db._submission is not None
    assert db._submission.user_id == user.id


def test_account_submission_returns_start_number(client_with_storage: TestClient):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeDualDb(_form(), start_number=77, user=user, profile=profile)
    app.dependency_overrides[get_db] = async_get_db_override(db)

    response = client_with_storage.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN, **_bearer(user)},
        json=_payload(),
    )

    assert response.status_code == 201
    assert response.json()["start_number"] == 77


def test_account_submission_updates_profile_in_db(client_with_storage: TestClient):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeDualDb(_form(), start_number=55, user=user, profile=profile)
    app.dependency_overrides[get_db] = async_get_db_override(db)

    response = client_with_storage.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN, **_bearer(user)},
        json=_payload(),
    )

    assert response.status_code == 201
    assert user.first_name == "Jan"
    assert user.last_name == "Kowalski"
    assert profile.vehicles_json["car"]["brand_model"] == "BMW M3"


def test_guest_submission_without_jwt_still_guest(client_with_storage: TestClient):
    from tests.fakes.async_db import FakeAsyncSubmissionDb

    form = _form()
    db = FakeAsyncSubmissionDb(form, start_number=42)
    app.dependency_overrides[get_db] = async_get_db_override(db)

    response = client_with_storage.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["mode"] == "guest"
    assert payload["start_number"] == 42
