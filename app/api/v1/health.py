from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Zwraca stan aplikacji i polaczenia z baza danych.",
)
async def health(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str | bool]:
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "timezone": settings.start_number_timezone,
        "print_enabled": settings.print_enabled,
        "database": db_status,
    }
