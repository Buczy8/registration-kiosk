import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.db.session import get_db
from app.schemas.submission import GuestSubmissionCreate
from app.services.submissions import create_guest_submission, get_missing_required_fields
from main import app
from tests.conftest import TEST_KIOSK_TOKEN
from tests.fakes.async_db import FakeAsyncSubmissionDb, async_get_db_override
from tests.fixtures.guest_registration_samples import (
    GUEST_REGISTRATION_SCHEMA,
    SAMPLE_GUEST_SUBMISSIONS,
    guest_registration_form,
)


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
    client_with_storage: TestClient,
    kiosk_settings_with_storage: Settings,
    index: int,
):
    form = guest_registration_form()
    start_number = index + 1
    db = FakeAsyncSubmissionDb(form, start_number=start_number)
    app.dependency_overrides[get_db] = async_get_db_override(db)

    response = client_with_storage.post(
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
    client_with_storage: TestClient,
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

    response = client_with_storage.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=incomplete_payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
    assert "Missing required form fields:" in response.json()["error"]["message"]


def test_create_guest_submission_service_persists_full_payload(
    kiosk_settings_with_storage: Settings,
):
    form = guest_registration_form()
    db = FakeAsyncSubmissionDb(form, start_number=7)

    submission = asyncio.run(
        create_guest_submission(
            db=db,
            data=GuestSubmissionCreate(**SAMPLE_GUEST_SUBMISSIONS[0]),
            settings=kiosk_settings_with_storage,
        )
    )

    assert submission.mode.value == "guest"
    assert submission.start_number == 7
    assert submission.payload_json["email"] == "jan.kowalski@example.com"
    assert submission.payload_json["vehicle_registration_number"] == "WX 12345"
