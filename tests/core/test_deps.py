from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.deps import get_current_user, get_current_user_id_from_token
from app.core.security import create_access_token
from app.models.user import User
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN
from tests.fakes.async_db import FakeAsyncDb


def _settings(*, secret: str = TEST_JWT_SECRET) -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=secret,
    )


def test_get_current_user_id_from_token_missing_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id_from_token(token=None, settings=_settings())

    assert exc_info.value.status_code == 401


def test_get_current_user_id_from_token_invalid_secret_raises_401():
    user_id = uuid4()
    token = create_access_token(user_id, _settings(secret="another-jwt-secret-key-min-32-chars"))

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id_from_token(token=token, settings=_settings())

    assert exc_info.value.status_code == 401


def test_get_current_user_non_existing_user_raises_401():
    user_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(db=FakeAsyncDb(None), user_id=user_id))

    assert exc_info.value.status_code == 401


def test_get_current_user_inactive_user_raises_403():
    user_id = uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        password_hash="hash",
        is_active=False,
        failed_login_count=0,
        locked_until=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(db=FakeAsyncDb(user), user_id=user_id))

    assert exc_info.value.status_code == 403


def test_get_current_user_locked_user_raises_423():
    user_id = uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        password_hash="hash",
        is_active=True,
        failed_login_count=0,
        locked_until=datetime.now(UTC) + timedelta(minutes=5),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(db=FakeAsyncDb(user), user_id=user_id))

    assert exc_info.value.status_code == 423

