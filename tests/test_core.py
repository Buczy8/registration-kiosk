import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import constant_time_equals, generate_secret, sha256_hex
from app.db.session import get_db
from main import app
from tests.fakes.async_db import FakeHealthyDb, async_get_db_override


def test_health_is_available_under_api_v1_and_adds_security_headers():
    app.dependency_overrides[get_db] = async_get_db_override(FakeHealthyDb())
    client = TestClient(app)

    try:
        response = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-request-id"]


def test_unhandled_routes_return_consistent_error_envelope():
    client = TestClient(app)

    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Not Found",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_production_config_rejects_debug_and_placeholder_secrets():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            debug=True,
            kiosk_token="change-me-kiosk-token-min-16-chars",
            jwt_secret_key="change-me-jwt-secret-key-min-32-characters-long",
        )


def test_security_helpers_compare_hash_and_generate_secrets():
    assert constant_time_equals("same-token", "same-token")
    assert not constant_time_equals("same-token", "other-token")
    assert sha256_hex("payload") == (
        "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"
    )
    assert len(generate_secret()) >= 32
