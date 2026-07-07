import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.session import get_db
from main import app


@pytest.fixture
def client(kiosk_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: kiosk_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client_with_storage(kiosk_settings_with_storage: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: kiosk_settings_with_storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)
