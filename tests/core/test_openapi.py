from fastapi.testclient import TestClient

from app.core.app import create_app
from app.core.deps import KIOSK_TOKEN_HEADER
from tests.conftest import dev_settings, prod_settings


def test_swagger_ui_is_available_in_development():
    client = TestClient(create_app(dev_settings()))

    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_openapi_schema_contains_kiosk_security_scheme():
    client = TestClient(create_app(dev_settings()))

    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "KioskAPI"
    assert schema["info"]["version"] == "0.1.0"
    assert "KioskToken" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["KioskToken"]["name"] == KIOSK_TOKEN_HEADER

    ping_path = schema["paths"]["/api/v1/kiosk/ping"]["get"]
    assert {"KioskToken": []} in ping_path["security"]


def test_openapi_schema_contains_kiosk_guest_endpoints():
    client = TestClient(create_app(dev_settings()))

    schema = client.get("/openapi.json").json()

    forms_path = schema["paths"]["/api/v1/kiosk/forms/active"]["get"]
    assert {"KioskToken": []} in forms_path["security"]

    submissions_path = schema["paths"]["/api/v1/kiosk/submissions"]["post"]
    assert {"KioskToken": []} in submissions_path["security"]


def test_openapi_schema_contains_auth_register_endpoint():
    client = TestClient(create_app(dev_settings()))
    schema = client.get("/openapi.json").json()

    assert "/api/v1/auth/register" in schema["paths"]


def test_openapi_schema_contains_auth_login_endpoint():
    client = TestClient(create_app(dev_settings()))
    schema = client.get("/openapi.json").json()

    assert "/api/v1/auth/login" in schema["paths"]


def test_openapi_auth_endpoints_require_kiosk_token_security():
    client = TestClient(create_app(dev_settings()))
    schema = client.get("/openapi.json").json()

    register_path = schema["paths"]["/api/v1/auth/register"]["post"]
    login_path = schema["paths"]["/api/v1/auth/login"]["post"]
    reset_req_path = schema["paths"]["/api/v1/auth/password-reset/request"]["post"]
    reset_confirm_path = schema["paths"]["/api/v1/auth/password-reset/confirm"]["post"]

    assert {"KioskToken": []} in register_path["security"]
    assert {"KioskToken": []} in login_path["security"]
    assert {"KioskToken": []} in reset_req_path["security"]
    assert {"KioskToken": []} in reset_confirm_path["security"]


def test_openapi_schema_contains_me_endpoints():
    client = TestClient(create_app(dev_settings()))
    schema = client.get("/openapi.json").json()

    assert "/api/v1/me/profile" in schema["paths"]
    assert "/api/v1/me/form-prefill" in schema["paths"]


def test_openapi_me_endpoints_require_kiosk_and_bearer_security():
    client = TestClient(create_app(dev_settings()))
    schema = client.get("/openapi.json").json()

    profile_path = schema["paths"]["/api/v1/me/profile"]["get"]
    prefill_path = schema["paths"]["/api/v1/me/form-prefill"]["get"]

    assert {"KioskToken": []} in profile_path["security"]
    assert {"HTTPBearer": []} in profile_path["security"]
    assert {"OAuth2PasswordBearer": []} in profile_path["security"]

    assert {"KioskToken": []} in prefill_path["security"]
    assert {"HTTPBearer": []} in prefill_path["security"]
    assert {"OAuth2PasswordBearer": []} in prefill_path["security"]


def test_openapi_docs_are_disabled_in_production():
    client = TestClient(create_app(prod_settings()))

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
