from pathlib import Path

import pytest

from app.core.config import Settings

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


def dev_settings() -> Settings:
    return Settings(
        app_env="development",
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


def prod_settings() -> Settings:
    return Settings(
        app_env="production",
        debug=False,
        kiosk_token="prod-kiosk-token-16chars",
        jwt_secret_key="prod-jwt-secret-key-min-32-chars-long",
    )


@pytest.fixture
def kiosk_settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


@pytest.fixture
def kiosk_settings_with_storage(tmp_path: Path) -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        start_number_timezone="Europe/Warsaw",
        storage_root=tmp_path,
    )
