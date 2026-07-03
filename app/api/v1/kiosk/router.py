from fastapi import APIRouter

from app.core.deps import KioskAuth

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@router.get(
    "/ping",
    summary="Ping kiosku",
    description="Weryfikuje poprawnosc tokenu kiosku (X-Kiosk-Token).",
    responses={
        401: {
            "description": "Brak lub niepoprawny token kiosku",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "unauthorized",
                            "message": "Invalid or missing kiosk token",
                            "request_id": "abc123",
                        }
                    }
                }
            },
        },
    },
)
def kiosk_ping(_: KioskAuth) -> dict[str, str]:
    return {"status": "ok"}
