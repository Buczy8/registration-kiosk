from fastapi import APIRouter

from app.core.deps import KioskAuth

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@router.get("/ping")
def kiosk_ping(_: KioskAuth) -> dict[str, str]:
    return {"status": "ok"}
