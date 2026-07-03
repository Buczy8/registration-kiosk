import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.db.session import get_db
from app.models.submission import Submission
from app.services.submissions import create_guest_submission, get_missing_required_fields
from main import app
from tests.guest_registration_samples import (
    GUEST_REGISTRATION_SCHEMA,
    SAMPLE_GUEST_SUBMISSIONS,
    guest_registration_form,
)

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _SubmissionDb:
    def __init__(self, form, *, start_number: int = 1):
        self.form = form
        self.start_number = start_number
        self.added: list[Submission] = []

    def execute(self, statement, params=None):
        if "next_start_number" in str(statement):
            return _Result(self.start_number)
        return _Result(self.form)

    def add(self, submission: Submission) -> None:
        self.added.append(submission)

    def flush(self) -> None:
        for submission in self.added:
            if submission.id is None:
                submission.id = uuid.uuid4()

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, submission: Submission) -> None:
        submission.id = uuid.uuid4()


@pytest.fixture
def kiosk_settings(tmp_path) -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        start_number_timezone="Europe/Warsaw",
        storage_root=tmp_path,
    )


@pytest.fixture
def client(kiosk_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: kiosk_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)


def _fake_get_db(db: _SubmissionDb):
    def override_get_db() -> Generator[_SubmissionDb, None, None]:
        yield db

    return override_get_db


@pytest.mark.parametrize("submission_payload", SAMPLE_GUEST_SUBMISSIONS)
def test_full_guest_registration_payload_has_no_missing_required_fields(
    submission_payload: dict,
):
    missing = get_missing_required_fields(
        GUEST_REGISTRATION_SCHEMA,
        submission_payload["payload_json"],
    )

    assert missing == []


@pytest.mark.parametrize("index", range(len(SAMPLE_GUEST_SUBMISSIONS)))
def test_create_guest_submission_accepts_full_registration_payload(
    client: TestClient,
    kiosk_settings: Settings,
    index: int,
):
    form = guest_registration_form()
    start_number = index + 1
    db = _SubmissionDb(form, start_number=start_number)
    app.dependency_overrides[get_db] = _fake_get_db(db)

    response = client.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=SAMPLE_GUEST_SUBMISSIONS[index],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["mode"] == "guest"
    assert payload["status"] == "submitted"
    assert payload["start_number"] == start_number
    assert payload["participant_role"] == SAMPLE_GUEST_SUBMISSIONS[index]["participant_role"]
    assert payload["vehicle_type"] == SAMPLE_GUEST_SUBMISSIONS[index]["vehicle_type"]
    assert len(db.added) == 1
    assert db.added[0].payload_json == SAMPLE_GUEST_SUBMISSIONS[index]["payload_json"]


def test_create_guest_submission_returns_400_for_incomplete_registration_payload(
    client: TestClient,
):
    form = guest_registration_form()
    app.dependency_overrides[get_db] = _fake_get_db(_SubmissionDb(form))
    incomplete_payload = {
        **SAMPLE_GUEST_SUBMISSIONS[0],
        "payload_json": {
            "first_name": "Jan",
            "last_name": "Kowalski",
            "pesel": "90010112345",
        },
    }

    response = client.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=incomplete_payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
    assert "Missing required form fields:" in response.json()["error"]["message"]


def test_create_guest_submission_service_persists_full_payload(kiosk_settings: Settings):
    form = guest_registration_form()
    db = _SubmissionDb(form, start_number=7)
    from app.schemas.submission import GuestSubmissionCreate

    submission = create_guest_submission(
        db=db,
        data=GuestSubmissionCreate(**SAMPLE_GUEST_SUBMISSIONS[0]),
        settings=kiosk_settings,
    )

    assert submission.mode.value == "guest"
    assert submission.start_number == 7
    assert submission.payload_json["email"] == "jan.kowalski@example.com"
    assert submission.payload_json["vehicle_registration_number"] == "WX 12345"
