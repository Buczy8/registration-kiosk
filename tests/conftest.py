from pathlib import Path
import uuid

import pytest
from sqlalchemy import event, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import DefaultClause

from app.core.config import Settings
from app.models.base import Base
from app.models.form import Form

TEST_KIOSK_TOKEN = "test-kiosk-token-16c"
TEST_JWT_SECRET = "test-jwt-secret-key-min-32-chars-long"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    """Allow PostgreSQL JSONB columns in sqlite test DB."""
    return "JSON"


def dev_settings() -> Settings:
    return Settings(
        app_env="development",
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


def prod_settings() -> Settings:
    return Settings(
        app_env="production",
        debug=False,
        kiosk_token="prod-kiosk-token-16chars",
        jwt_secret_key="prod-jwt-secret-key-min-32-chars-long",
    )


@pytest.fixture
def kiosk_settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


@pytest.fixture
def kiosk_settings_with_storage(tmp_path: Path) -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        start_number_timezone="Europe/Warsaw",
        storage_root=tmp_path,
    )


@pytest.fixture
async def async_session():
    """Async session fixture for unit tests with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_functions(dbapi_connection, _connection_record):
        # Keep Postgres server defaults usable in sqlite tests.
        dbapi_connection.create_function("gen_random_uuid", 0, lambda: uuid.uuid4().hex)

    # Strip PostgreSQL casts from defaults so sqlite can create schema.
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.server_default is None:
                continue
            default_arg = getattr(column.server_default, "arg", column.server_default)
            default_text = getattr(default_arg, "text", None)
            if default_text and "::jsonb" in default_text:
                column.server_default = DefaultClause(
                    text(default_text.replace("::jsonb", ""))
                )
    
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def active_form() -> Form:
    """Active form fixture for tests."""
    return Form(
        id=uuid.uuid4(),
        code="participant-universal",
        name="Oświadczenie uczestnika",
        version="2.0",
        schema_json={
            "required": ["first_name", "last_name"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
            },
        },
        pdf_template_path="templates/forms/participant-v2.pdf",
        is_active=True,
    )


@pytest.fixture(autouse=True)
def mock_printer_printing(request, monkeypatch):
    """Automatically mock printer printing and health check in tests to avoid socket connection errors, except in test_printer.py."""
    if "test_printer.py" in str(request.node.fspath):
        return

    async def _mock_print(*args, **kwargs):
        pass

    async def _mock_health(*args, **kwargs):
        return True

    monkeypatch.setattr(
        "app.services.printer.send_print_job",
        _mock_print
    )
    monkeypatch.setattr(
        "app.services.printer.get_printer_health",
        _mock_health
    )

