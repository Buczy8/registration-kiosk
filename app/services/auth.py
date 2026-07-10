from __future__ import annotations

from datetime import UTC

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    verify_password,
)
from app.schemas.auth import (
    AuthServiceResult,
    LoginRequest,
    RegisterRequest,
    UserPublic,
)
from app.services.users import (
    create_user,
    get_user_by_email,
    is_account_locked,
    record_failed_login,
    reset_failed_login,
)

AUTH_FAILURE_MESSAGE = "Invalid email or password"


def _auth_response(user_id, email: str, settings: Settings) -> AuthServiceResult:
    return AuthServiceResult(
        access_token=create_access_token(user_id, settings),
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserPublic(user_id=user_id, email=email),
    )


async def register(
    db: AsyncSession,
    data: RegisterRequest,
    settings: Settings,
) -> AuthServiceResult:
    existing_user = await get_user_by_email(db, data.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = await create_user(db, data)
    return _auth_response(user.id, user.email, settings)


async def login(
    db: AsyncSession,
    data: LoginRequest,
    settings: Settings,
) -> AuthServiceResult:
    user = await get_user_by_email(db, data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_FAILURE_MESSAGE,
        )

    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked",
        )

    if not verify_password(data.password, user.password_hash):
        await record_failed_login(db, user, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_FAILURE_MESSAGE,
        )

    # Preserve scalar values before commit (commit expires ORM attributes).
    user_id = user.id
    user_email = user.email
    await reset_failed_login(db, user)
    return _auth_response(user_id, user_email, settings)


