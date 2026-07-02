from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings

settings = get_settings()
from app.db.session import engine, get_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_storage_dirs()
    yield
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
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
