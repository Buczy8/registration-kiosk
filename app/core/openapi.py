from __future__ import annotations

from typing import Any

from app.core.config import Settings

API_DESCRIPTION = """
Backend API dla kiosku rejestracyjnego.

## Autoryzacja

Endpointy kiosku wymagaja naglowka `X-Kiosk-Token`.
Uzyc przycisku **Authorize** w Swagger UI i wkleic wartosc z `KIOSK_TOKEN`.

## Bledy

Wszystkie bledy zwracaja spójny format JSON:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Invalid or missing kiosk token",
    "request_id": "..."
  }
}
```
"""

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "health",
        "description": "Sprawdzanie stanu aplikacji i polaczenia z baza danych.",
    },
    {
        "name": "kiosk",
        "description": "Endpointy kiosku (tablet). Wymagaja naglowka X-Kiosk-Token.",
    },
]


def docs_enabled(settings: Settings) -> bool:
    return settings.app_env != "production"


def fastapi_openapi_kwargs(settings: Settings) -> dict[str, Any]:
    enabled = docs_enabled(settings)
    return {
        "title": settings.app_name,
        "version": settings.app_version,
        "description": API_DESCRIPTION,
        "openapi_tags": OPENAPI_TAGS,
        "docs_url": "/docs" if enabled else None,
        "redoc_url": "/redoc" if enabled else None,
        "openapi_url": "/openapi.json" if enabled else None,
    }
