import uuid
from collections.abc import Generator
from datetime import date

import pytest
import fitz
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.db.session import get_db
from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.models.form import Form
from app.models.submission import Submission
from main import app
from tests.signature_samples import sample_signature_base64

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
    def __init__(self, form: Form, *, start_number: int = 42, existing_submission: Submission | None = None):
        self.form = form
        self.start_number = start_number
        self.sequence_date = date(2026, 7, 3)
        self._existing_submission = existing_submission

    def execute(self, statement, params=None):
        if "next_start_number" in str(statement):
            return _Result(self.start_number)
        if "FROM submissions" in str(statement):
            return _Result(self._existing_submission)
        return _Result(self.form)

    def add(self, submission: Submission) -> None:
        self._submission = submission

    def flush(self) -> None:
        if hasattr(self, "_submission") and self._submission.id is None:
            self._submission.id = uuid.uuid4()

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, submission: Submission) -> None:
        submission.id = uuid.uuid4()


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


def _template_pdf(path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    for field_name, rect, field_type in [
        ("checkbox_26aqhm", fitz.Rect(10, 10, 20, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_29pnyu", fitz.Rect(30, 10, 40, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("text_8fpaj", fitz.Rect(10, 40, 180, 60), fitz.PDF_WIDGET_TYPE_TEXT),
    ]:
        widget = fitz.Widget()
        widget.field_name = field_name
        widget.field_type = field_type
        widget.rect = rect
        page.add_widget(widget)
    doc.save(path)
    doc.close()


def _valid_payload(**overrides) -> dict:
    return {
        "participant_role": "driver",
        "vehicle_type": "car",
        "payload_json": {"first_name": "Jan", "last_name": "Kowalski"},
        "consents_json": {"terms": True},
        "declarations_accepted": True,
        "signature_image_base64": sample_signature_base64(),
        **overrides,
    }


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


def test_create_guest_submission_requires_token(client: TestClient):
    response = client.post("/api/v1/kiosk/submissions", json=_valid_payload())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_create_guest_submission_returns_201_for_valid_request(client: TestClient):
    form = _form()
    db = _SubmissionDb(form, start_number=42)
    app.dependency_overrides[get_db] = _fake_get_db(db)

    response = client.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_valid_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["form_id"] == str(form.id)
    assert payload["form_version"] == "1.0"
    assert payload["start_number"] == 42
    assert payload["sequence_date"]
    assert payload["status"] == "submitted"
    assert payload["mode"] == "guest"
    assert db._submission.signature_path is not None
    assert db._submission.signature_hash is not None
    assert db._submission.signed_at is not None


def test_create_guest_submission_returns_422_for_invalid_enum(client: TestClient):
    form = _form()
    app.dependency_overrides[get_db] = _fake_get_db(_SubmissionDb(form))

    response = client.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_valid_payload(vehicle_type="truck"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_guest_submission_returns_422_when_declarations_not_accepted(client: TestClient):
    form = _form()
    app.dependency_overrides[get_db] = _fake_get_db(_SubmissionDb(form))

    response = client.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_valid_payload(declarations_accepted=False),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_guest_submission_returns_400_when_required_fields_missing(client: TestClient):
    form = _form()
    app.dependency_overrides[get_db] = _fake_get_db(_SubmissionDb(form))

    response = client.post(
        "/api/v1/kiosk/submissions",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
        json=_valid_payload(payload_json={"first_name": "Jan"}),
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Missing required form fields: last_name",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_generate_guest_pdf_requires_token(client: TestClient):
    response = client.get(f"/api/v1/kiosk/submissions/{uuid.uuid4()}/pdf")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_generate_guest_pdf_returns_pdf_for_guest_submission(client: TestClient, tmp_path):
    template_path = tmp_path / "guest-registration.pdf"
    _template_pdf(template_path)
    form = _form()
    form.pdf_template_path = str(template_path)
    submission = Submission(
        id=uuid.uuid4(),
        form_id=form.id,
        form=form,
        form_version=form.version,
        user_id=None,
        filled_for_related_person_id=None,
        mode=SubmissionMode.GUEST,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=77,
        sequence_date=date(2026, 7, 3),
        payload_json={"first_name": "Jan", "last_name": "Kowalski"},
        consents_json={"terms": True},
        declarations_accepted=True,
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )
    db = _SubmissionDb(form, existing_submission=submission)
    app.dependency_overrides[get_db] = _fake_get_db(db)

    response = client.get(
        f"/api/v1/kiosk/submissions/{submission.id}/pdf",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="submission-77.pdf"' == response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")


def test_generate_guest_pdf_returns_404_for_account_submission(client: TestClient):
    form = _form()
    submission = Submission(
        id=uuid.uuid4(),
        form_id=form.id,
        form_version=form.version,
        user_id=uuid.uuid4(),
        filled_for_related_person_id=None,
        mode=SubmissionMode.ACCOUNT,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=90,
        sequence_date=date(2026, 7, 3),
        payload_json={"first_name": "Jan", "last_name": "Kowalski"},
        consents_json={"terms": True},
        declarations_accepted=True,
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )
    app.dependency_overrides[get_db] = _fake_get_db(_SubmissionDb(form, existing_submission=submission))

    response = client.get(
        f"/api/v1/kiosk/submissions/{submission.id}/pdf",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
