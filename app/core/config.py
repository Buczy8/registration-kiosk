from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql+psycopg_async://kiosk:kiosk@localhost:5432/kiosk"
PLACEHOLDER_KIOSK_TOKEN = "change-me-kiosk-token-min-16-chars"
PLACEHOLDER_JWT_SECRET_KEY = "change-me-jwt-secret-key-min-32-characters-long"
_SECRET_COMPLEXITY_RE = re.compile(r"[A-Za-z].*[0-9]|[0-9].*[A-Za-z]")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplikacja ---
    app_name: str = "KioskAPI"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Serwer ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Baza danych ---
    database_url: str = DEFAULT_DATABASE_URL

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # --- Kiosk (tablet) ---
    kiosk_token: str = Field(min_length=16)

    # --- JWT ---
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    auth_cookie_name: str = "kiosk_access_token"
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    auth_cookie_secure: bool = False
    trusted_hosts: list[str] = Field(default_factory=lambda: ["*"])

    # --- Numer startowy ---
    start_number_timezone: str = "Europe/Warsaw"

    # --- Drukarka ---
    printer_name: str = "default"
    printer_host: str = "localhost"
    printer_port: int = 9100
    print_enabled: bool = True
    # Symulacja drukowania (brak fizycznej drukarki na dev/lokalnie).
    # Domyślnie: od razu sukces (żeby nie wydłużać testów).
    print_simulation_delay_seconds: float = Field(default=0, ge=0)
    print_simulation_failure_probability: float = Field(default=0, ge=0, le=1)

    # --- Pliki (PDF, podpisy) ---
    storage_root: Path = Field(default=PROJECT_ROOT / "storage")
    pdf_storage_dir: str = "pdfs"
    signature_storage_dir: str = "signatures"
    form_templates_dir: Path = Field(default=PROJECT_ROOT / "templates" / "forms")

    # --- Bezpieczenstwo logowania ---
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    login_rate_limit_window_seconds: int = 60
    login_rate_limit_max_requests: int = 10

    # --- Kiosk UX ---
    kiosk_idle_logout_seconds: int = 30

    @field_validator("storage_root", "form_templates_dir", mode="before")
    @classmethod
    def expand_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @property
    def pdf_dir(self) -> Path:
        return self.storage_root / self.pdf_storage_dir

    @property
    def signature_dir(self) -> Path:
        return self.storage_root / self.signature_storage_dir

    @property
    def effective_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    def ensure_storage_dirs(self) -> None:
        for directory in (
            self.storage_root,
            self.pdf_dir,
            self.signature_dir,
            self.form_templates_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @model_validator(mode="after")
    def validate_production_safety(self) -> Settings:
        if self.app_env != "production":
            return self

        errors: list[str] = []
        if self.debug:
            errors.append("DEBUG must be false in production")
        if self.kiosk_token == PLACEHOLDER_KIOSK_TOKEN:
            errors.append("KIOSK_TOKEN must be changed in production")
        if self.jwt_secret_key == PLACEHOLDER_JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY must be changed in production")
        if len(set(self.kiosk_token)) < 8 or not _SECRET_COMPLEXITY_RE.search(self.kiosk_token):
            errors.append(
                "KIOSK_TOKEN must contain mixed alphanumeric characters and enough entropy"
            )
        if len(set(self.jwt_secret_key)) < 12 or not _SECRET_COMPLEXITY_RE.search(self.jwt_secret_key):
            errors.append(
                "JWT_SECRET_KEY must contain mixed alphanumeric characters and enough entropy"
            )
        if not self.auth_cookie_secure:
            self.auth_cookie_secure = True
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            errors.append("AUTH_COOKIE_SAMESITE=none requires AUTH_COOKIE_SECURE=true")
        if errors:
            raise ValueError("; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    """URL bazy bez pelnej walidacji Settings (np. dla Alembica)."""
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("database_url")
        or DEFAULT_DATABASE_URL
    )


__all__ = ["Settings", "get_database_url", "get_settings"]
