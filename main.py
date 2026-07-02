from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "timezone": settings.start_number_timezone,
        "print_enabled": settings.print_enabled,
    }
