from fastapi.testclient import TestClient

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
