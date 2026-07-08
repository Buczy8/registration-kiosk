from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import KioskAuth
from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
)
from app.services.auth import (
    confirm_password_reset,
    login,
    register,
    request_password_reset,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
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


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Żądanie resetu hasła",
)
async def password_reset_request_endpoint(
    data: PasswordResetRequest,
    _: KioskAuth,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    return await request_password_reset(db=db, data=data, settings=settings)


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Potwierdzenie resetu hasła",
)
async def password_reset_confirm_endpoint(
    data: PasswordResetConfirm,
    _: KioskAuth,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    return await confirm_password_reset(db=db, data=data)

