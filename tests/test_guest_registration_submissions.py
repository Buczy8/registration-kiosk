import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.db.session import get_db
from app.schemas.submission import GuestSubmissionCreate
from app.services.submissions import create_guest_submission, get_missing_required_fields
from main import app
from tests.fakes.async_db import FakeAsyncSubmissionDb, async_get_db_override
from tests.guest_registration_samples import (
    GUEST_REGISTRATION_SCHEMA,
    SAMPLE_GUEST_SUBMISSIONS,
    guest_registration_form,
)

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


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
    db = FakeAsyncSubmissionDb(form, start_number=start_number)
    app.dependency_overrides[get_db] = async_get_db_override(db)

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
    app.dependency_overrides[get_db] = async_get_db_override(FakeAsyncSubmissionDb(form))
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
    db = FakeAsyncSubmissionDb(form, start_number=7)

    submission = asyncio.run(
        create_guest_submission(
            db=db,
            data=GuestSubmissionCreate(**SAMPLE_GUEST_SUBMISSIONS[0]),
            settings=kiosk_settings,
        )
    )

    assert submission.mode.value == "guest"
    assert submission.start_number == 7
    assert submission.payload_json["email"] == "jan.kowalski@example.com"
    assert submission.payload_json["vehicle_registration_number"] == "WX 12345"
