import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_config_rejects_debug_and_placeholder_secrets():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            debug=True,
            kiosk_token="change-me-kiosk-token-min-16-chars",
            jwt_secret_key="change-me-jwt-secret-key-min-32-characters-long",
        )
