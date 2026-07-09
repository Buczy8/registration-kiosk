from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import KioskAuth
from app.core.rate_limit import SlidingWindowRateLimiter, build_rate_limit_key
from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
)
from app.services.auth import (
    login,
    register,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_login_rate_limiter: SlidingWindowRateLimiter | None = None


def _get_login_rate_limiter(settings: Settings) -> SlidingWindowRateLimiter:
    global _login_rate_limiter
    if _login_rate_limiter is None:
        _login_rate_limiter = SlidingWindowRateLimiter(
            max_requests=settings.login_rate_limit_max_requests,
            window_seconds=settings.login_rate_limit_window_seconds,
        )
    return _login_rate_limiter


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rejestracja konta użytkownika",
)
async def register_endpoint(
    data: RegisterRequest,
    _: KioskAuth,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    auth_response = await register(db=db, data=data, settings=settings)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=auth_response.access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=auth_response.expires_in,
    )
    return auth_response


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Logowanie użytkownika",
)
async def login_endpoint(
    data: LoginRequest,
    _: KioskAuth,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = build_rate_limit_key("login", data.email, client_ip)
    _get_login_rate_limiter(settings).check(rate_limit_key)
    auth_response = await login(db=db, data=data, settings=settings)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=auth_response.access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=auth_response.expires_in,
    )
    return auth_response


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Wylogowanie użytkownika",
)
async def logout_endpoint(
    _: KioskAuth,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    return MessageResponse(message="Logged out")



