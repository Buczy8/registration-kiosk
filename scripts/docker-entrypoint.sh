#!/bin/sh
set -e

cd /app

echo "Running database migrations..."
uv run alembic upgrade head

echo "Seeding active form..."
uv run python scripts/seed_active_form.py

echo "Starting KioskAPI on ${HOST:-0.0.0.0}:${PORT:-8000}..."
exec uv run uvicorn main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
