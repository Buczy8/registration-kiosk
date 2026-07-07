import asyncio
import uuid
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.models.form import Form
from app.models.submission import Submission
from app.models.user import User, UserProfile
from app.schemas.submission import AccountSubmissionCreate, GuestSubmissionCreate
from app.services.submissions import (
    create_account_submission,
    create_guest_submission,
    get_missing_required_fields,
    get_next_start_number,
    get_sequence_date,
)
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN
from tests.fakes.async_db import FakeAsyncDb, FakeAsyncSubmissionDb, FakeResult
from tests.fixtures.signature_samples import sample_signature_base64


def _settings(storage_root: Path | None = None) -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        start_number_timezone="Europe/Warsaw",
        storage_root=storage_root or Path.cwd() / "storage",
    )


def _form(**overrides) -> Form:
    defaults = {
        "id": uuid.uuid4(),
        "code": "guest-registration",
        "name": "Rejestracja gościa",
        "version": "1.0",
        "schema_json": {
            "required": ["first_name", "last_name"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
            },
        },
        "pdf_template_path": "templates/forms/guest-registration-v1.pdf",
        "is_active": True,
    }
    defaults.update(overrides)
    return Form(**defaults)


def _guest_data(**overrides) -> GuestSubmissionCreate:
    payload = {
        "participant_role": ParticipantRole.DRIVER,
        "vehicle_type": VehicleType.CAR,
        "payload_json": {"first_name": "Jan", "last_name": "Kowalski"},
        "consents_json": {"terms": True},
        "declarations_accepted": True,
        "signature_image_base64": sample_signature_base64(),
    }
    payload.update(overrides)
    return GuestSubmissionCreate(**payload)


def test_get_missing_required_fields_returns_missing_fields():
    missing = get_missing_required_fields(
        {"required": ["first_name", "last_name", "birth_date"]},
        {"first_name": "Jan"},
    )

    assert missing == ["last_name", "birth_date"]


def test_get_missing_required_fields_ignores_non_string_required_entries():
    missing = get_missing_required_fields(
        {"required": ["first_name", 123, None]},
        {},
    )

    assert missing == ["first_name"]


def test_get_missing_required_fields_returns_empty_list_when_required_is_not_list():
    assert get_missing_required_fields({"required": "first_name"}, {}) == []
    assert get_missing_required_fields({"required": None}, {}) == []


def test_get_sequence_date_returns_date():
    result = get_sequence_date(_settings())

    assert isinstance(result, date)


def test_get_sequence_date_accepts_europe_warsaw_timezone():
    get_sequence_date(_settings())


def test_get_next_start_number_returns_int_from_db():
    db = FakeAsyncDb(7)

    result = asyncio.run(get_next_start_number(db, date(2026, 7, 3)))

    assert result == 7


def test_get_next_start_number_uses_next_start_number_query():
    db = FakeAsyncDb(7)
    sequence_date = date(2026, 7, 3)

    asyncio.run(get_next_start_number(db, sequence_date))

    assert "next_start_number" in str(db.last_statement)
    assert db.last_params == {"sequence_date": sequence_date}


def test_create_guest_submission_creates_guest_submission(tmp_path):
    db = FakeAsyncSubmissionDb(_form(), start_number=7)

    submission = asyncio.run(
        create_guest_submission(db, _guest_data(), _settings(tmp_path))
    )

    assert submission.mode == SubmissionMode.GUEST
    assert submission.user_id is None
    assert submission.filled_for_related_person_id is None
    assert submission.form_version == "1.0"
    assert submission.start_number == 7
    assert submission.status == SubmissionStatus.SUBMITTED
    assert submission.signature_path is not None
    assert submission.signature_hash is not None
    assert submission.signed_at is not None
    assert db.committed is True
    assert db.refreshed == [submission]


def test_create_guest_submission_does_not_persist_when_required_fields_missing():
    db = FakeAsyncSubmissionDb(
        _form(schema_json={"required": ["first_name", "last_name"]}),
        start_number=7,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            create_guest_submission(
                db,
                _guest_data(payload_json={"first_name": "Jan"}),
                _settings(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Missing required form fields: last_name"
    assert db.added == []
    assert db.committed is False


def test_create_guest_submission_rolls_back_when_commit_fails(tmp_path):
    db = FakeAsyncSubmissionDb(
        _form(),
        start_number=7,
        commit_raises=RuntimeError("db error"),
    )

    with pytest.raises(RuntimeError, match="db error"):
        asyncio.run(create_guest_submission(db, _guest_data(), _settings(tmp_path)))

    assert db.rolled_back is True


def _account_data(**overrides) -> AccountSubmissionCreate:
    payload = {
        "participant_role": ParticipantRole.DRIVER,
        "vehicle_type": VehicleType.CAR,
        "payload_json": {
            "first_name": "Jan",
            "last_name": "Kowalski",
            "vehicle_brand_model": "BMW M3",
            "vehicle_registration_number": "WX 12345",
        },
        "consents_json": {"terms": True},
        "declarations_accepted": True,
        "signature_image_base64": sample_signature_base64(),
    }
    payload.update(overrides)
    return AccountSubmissionCreate(**payload)


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


class _FakeAccountDb:
    """Async session fake covering form, start_number and profile lookups."""

    def __init__(self, form: Form, *, start_number: int = 7, profile: UserProfile | None = None):
        self.form = form
        self.start_number = start_number
        self.profile = profile
        self.added: list = []
        self.committed = False
        self.rolled_back = False
        self.refreshed: list = []
        self._submission = None

    async def execute(self, statement, params=None):
        sql = str(statement)
        if "next_start_number" in sql:
            return FakeResult(self.start_number)
        if "user_profiles" in sql:
            return FakeResult(self.profile)
        return FakeResult(self.form)

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
        self.refreshed.append(obj)


def test_create_account_submission_sets_account_mode_and_user(tmp_path):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeAccountDb(_form(), start_number=15, profile=profile)

    submission = asyncio.run(
        create_account_submission(db, user, _account_data(), _settings(tmp_path))
    )

    assert submission.mode == SubmissionMode.ACCOUNT
    assert submission.user_id == user.id
    assert submission.start_number == 15
    assert submission.status == SubmissionStatus.SUBMITTED
    assert submission.signature_path is not None
    assert submission.signature_hash is not None
    assert db.committed is True


def test_create_account_submission_updates_profile(tmp_path):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeAccountDb(_form(), start_number=15, profile=profile)

    asyncio.run(create_account_submission(db, user, _account_data(), _settings(tmp_path)))

    assert user.first_name == "Jan"
    assert user.last_name == "Kowalski"
    assert profile.vehicles_json["car"]["brand_model"] == "BMW M3"
    assert profile.vehicles_json["car"]["registration_number"] == "WX 12345"


def test_create_account_submission_rolls_back_when_commit_fails(tmp_path):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeAccountDb(_form(), start_number=15, profile=profile)

    original_commit = db.commit

    async def failing_commit():
        raise RuntimeError("db error")

    db.commit = failing_commit

    with pytest.raises(RuntimeError, match="db error"):
        asyncio.run(create_account_submission(db, user, _account_data(), _settings(tmp_path)))

    assert db.rolled_back is True

    db.commit = original_commit


def test_create_account_submission_does_not_persist_when_required_fields_missing(tmp_path):
    user = _user()
    profile = UserProfile(user_id=user.id, vehicles_json={})
    db = _FakeAccountDb(
        _form(schema_json={"required": ["first_name", "last_name"]}),
        start_number=15,
        profile=profile,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            create_account_submission(
                db,
                user,
                _account_data(payload_json={"first_name": "Jan"}),
                _settings(tmp_path),
            )
        )

    assert exc_info.value.status_code == 400
    assert db.committed is False
