import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from main import app

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


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


def test_kiosk_ping_requires_token(client: TestClient):
    response = client.get("/api/v1/kiosk/ping")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Invalid or missing kiosk token",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_kiosk_ping_rejects_invalid_token(client: TestClient):
    response = client.get(
        "/api/v1/kiosk/ping",
        headers={KIOSK_TOKEN_HEADER: "wrong-kiosk-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_kiosk_ping_accepts_valid_token(client: TestClient):
    response = client.get(
        "/api/v1/kiosk/ping",
        headers={KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
