from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import constant_time_equals

KIOSK_TOKEN_HEADER = "X-Kiosk-Token"


def verify_kiosk_token(
    x_kiosk_token: str | None = Header(default=None, alias=KIOSK_TOKEN_HEADER),
    settings: Settings = Depends(get_settings),
) -> None:
    if x_kiosk_token is None or not constant_time_equals(
        x_kiosk_token,
        settings.kiosk_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing kiosk token",
        )


KioskAuth = Annotated[None, Depends(verify_kiosk_token)]
