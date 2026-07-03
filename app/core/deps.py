from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.security import constant_time_equals

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
