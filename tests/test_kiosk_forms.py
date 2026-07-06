import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.db.session import get_db
from app.models.form import Form
from main import app
from tests.fakes.async_db import FakeAsyncDb, async_get_db_override

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


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


@pytest.fixture
def kiosk_settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


@pytest.fixture
def client(kiosk_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: kiosk_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)


def test_active_form_requires_token(client: TestClient):
    response = client.get("/api/v1/kiosk/forms/active")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Invalid or missing kiosk token",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_active_form_returns_active_form_without_pdf_template_path(client: TestClient):
    form = _form()
    app.dependency_overrides[get_db] = async_get_db_override(FakeAsyncDb(form))

    response = client.get(
        "/api/v1/kiosk/forms/active",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "id": str(form.id),
        "code": "guest-registration",
        "name": "Rejestracja gościa",
        "version": "1.0",
        "schema_json": form.schema_json,
    }
    assert "pdf_template_path" not in payload


def test_active_form_returns_404_when_no_active_form(client: TestClient):
    app.dependency_overrides[get_db] = async_get_db_override(FakeAsyncDb(None))

    response = client.get(
        "/api/v1/kiosk/forms/active",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Active form not found",
            "request_id": response.headers["x-request-id"],
        }
    }
