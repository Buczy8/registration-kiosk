from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.user import PasswordResetToken
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
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

logger = logging.getLogger(__name__)

AUTH_FAILURE_MESSAGE = "Invalid email or password"
PASSWORD_RESET_MESSAGE = "If the email exists, password reset instructions will be sent"


def _auth_response(user, settings: Settings) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id, settings),
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserPublic(user_id=user.id, email=user.email),
    )


async def register(
    db: AsyncSession,
    data: RegisterRequest,
    settings: Settings,
) -> AuthResponse:
    existing_user = await get_user_by_email(db, data.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = await create_user(db, data)
    return _auth_response(user, settings)


async def login(
    db: AsyncSession,
    data: LoginRequest,
    settings: Settings,
) -> AuthResponse:
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

    await reset_failed_login(db, user)
    return _auth_response(user, settings)


async def request_password_reset(
    db: AsyncSession,
    data: PasswordResetRequest,
    settings: Settings,
) -> MessageResponse:
    user = await get_user_by_email(db, data.email)
    if user is None:
        return MessageResponse(message=PASSWORD_RESET_MESSAGE)

    raw_token = generate_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.now(UTC)
        + timedelta(minutes=settings.password_reset_token_expire_minutes),
        used_at=None,
    )
    db.add(reset_token)
    await db.commit()

    if not settings.smtp_host:
        logger.info("Password reset link for %s: /reset-password?token=%s", user.email, raw_token)

    return MessageResponse(message=PASSWORD_RESET_MESSAGE)


async def confirm_password_reset(
    db: AsyncSession,
    data: PasswordResetConfirm,
) -> MessageResponse:
    result = await db.execute(
        select(PasswordResetToken)
        .options(selectinload(PasswordResetToken.user))
        .where(
            PasswordResetToken.token_hash == hash_reset_token(data.token)
        )
    )
    reset_token = result.scalar_one_or_none()
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    now = datetime.now(UTC)
    if reset_token.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token expired",
        )
    if reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token already used",
        )

    reset_token.user.password_hash = hash_password(data.new_password)
    reset_token.user.failed_login_count = 0
    reset_token.user.locked_until = None
    reset_token.used_at = now
    await db.commit()

    return MessageResponse(message="Password has been reset")

