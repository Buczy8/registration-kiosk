from fastapi.testclient import TestClient

from main import app


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
