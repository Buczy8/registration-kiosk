from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Security, status
from fastapi.security import (
    APIKeyHeader,
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import constant_time_equals, decode_access_token
from app.db.session import get_db
from app.models.user import User

KIOSK_TOKEN_HEADER = "X-Kiosk-Token"


class KioskToken(APIKeyHeader):
    def __init__(self) -> None:
        super().__init__(
            name=KIOSK_TOKEN_HEADER,
            auto_error=False,
            description="Token autoryzacji kiosku. Wartosc ze zmiennej srodowiskowej KIOSK_TOKEN.",
        )


kiosk_token_scheme = KioskToken()


def verify_kiosk_token(
    token: str | None = Security(kiosk_token_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    if token is None or not constant_time_equals(token, settings.kiosk_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing kiosk token",
        )


KioskAuth = Annotated[None, Depends(verify_kiosk_token)]


# --- User auth (JWT Bearer) ---
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
    description="Bearer JWT (OAuth2 password flow).",
)
http_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Bearer JWT (Authorization: Bearer <token>).",
)


def _get_token_from_security_schemes(
    bearer: HTTPAuthorizationCredentials | None = Security(http_bearer_scheme),
    oauth2_token: str | None = Security(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias="kiosk_access_token"),
) -> str | None:
    if bearer is not None:
        return bearer.credentials
    if oauth2_token:
        return oauth2_token
    return cookie_token


def get_current_user_id_from_token(
    token: str | None = Depends(_get_token_from_security_schemes),
    settings: Settings = Depends(get_settings),
) -> UUID:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        return decode_access_token(token, settings)
    except Exception as e:
        # decode_access_token raises jwt.InvalidTokenError / jwt.ExpiredSignatureError
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
        ) from e


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id_from_token),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="User is locked",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_current_user(
    token: str | None = Depends(_get_token_from_security_schemes),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if token is None:
        return None
    user_id = get_current_user_id_from_token(token=token, settings=settings)
    return await get_current_user(db=db, user_id=user_id)


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


@dataclass(frozen=True)
class KioskAndUser:
    user: User


async def verify_kiosk_and_user(
    _: KioskAuth,
    user: CurrentUser,
) -> KioskAndUser:
    return KioskAndUser(user=user)
