import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.errors import register_exception_handlers
from app.schemas.submission import GuestSubmissionCreate


def _valid_payload(**overrides) -> dict:
    return {
        "participant_role": "driver",
        "vehicle_type": "car",
        "payload_json": {"first_name": "Jan", "last_name": "Kowalski"},
        "consents_json": {"terms": True},
        "declarations_accepted": True,
        **overrides,
    }


def test_declarations_accepted_false_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        GuestSubmissionCreate.model_validate(_valid_payload(declarations_accepted=False))

    assert any(error["loc"] == ("declarations_accepted",) for error in exc_info.value.errors())


def test_empty_payload_json_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        GuestSubmissionCreate.model_validate(_valid_payload(payload_json={}))

    assert any(error["loc"] == ("payload_json",) for error in exc_info.value.errors())


def test_invalid_vehicle_type_returns_fastapi_validation_error():
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/guest-submissions")
    def create_guest_submission(data: GuestSubmissionCreate) -> GuestSubmissionCreate:
        return data

    client = TestClient(app)
    response = client.post("/guest-submissions", json=_valid_payload(vehicle_type="truck"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
