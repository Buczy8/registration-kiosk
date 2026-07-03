from fastapi.testclient import TestClient

from app.core.app import create_app
from app.core.config import Settings
from app.core.deps import KIOSK_TOKEN_HEADER

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


def _dev_settings() -> Settings:
    return Settings(
        app_env="development",
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


def _prod_settings() -> Settings:
    return Settings(
        app_env="production",
        debug=False,
        kiosk_token="prod-kiosk-token-16chars",
        jwt_secret_key="prod-jwt-secret-key-min-32-chars-long",
    )


def test_swagger_ui_is_available_in_development():
    client = TestClient(create_app(_dev_settings()))

    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_openapi_schema_contains_kiosk_security_scheme():
    client = TestClient(create_app(_dev_settings()))

    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "KioskAPI"
    assert schema["info"]["version"] == "0.1.0"
    assert "KioskToken" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["KioskToken"]["name"] == KIOSK_TOKEN_HEADER

    ping_path = schema["paths"]["/api/v1/kiosk/ping"]["get"]
    assert {"KioskToken": []} in ping_path["security"]


def test_openapi_schema_contains_kiosk_guest_endpoints():
    client = TestClient(create_app(_dev_settings()))

    schema = client.get("/openapi.json").json()

    forms_path = schema["paths"]["/api/v1/kiosk/forms/active"]["get"]
    assert {"KioskToken": []} in forms_path["security"]

    submissions_path = schema["paths"]["/api/v1/kiosk/submissions"]["post"]
    assert {"KioskToken": []} in submissions_path["security"]


def test_openapi_docs_are_disabled_in_production():
    client = TestClient(create_app(_prod_settings()))

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
