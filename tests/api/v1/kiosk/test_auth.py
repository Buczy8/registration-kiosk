from fastapi.testclient import TestClient

from app.core.deps import KIOSK_TOKEN_HEADER
from tests.conftest import TEST_KIOSK_TOKEN


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
