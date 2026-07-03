from __future__ import annotations

import base64
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import fitz
from fastapi import HTTPException, status

from app.core.config import Settings

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DATA_URL_PREFIX = re.compile(r"^data:image/png;base64,", re.IGNORECASE)
MAX_SIGNATURE_BYTES = 512_000
MIN_SIGNATURE_WIDTH = 100
MIN_SIGNATURE_HEIGHT = 40
MIN_INK_PIXELS = 25


class SignatureValidationError(ValueError):
    pass


def decode_signature_image(signature_image_base64: str) -> bytes:
    normalized = DATA_URL_PREFIX.sub("", signature_image_base64.strip())
    if not normalized:
        raise SignatureValidationError("Signature image is required")

    try:
        image_bytes = base64.b64decode(normalized, validate=True)
    except Exception as exc:
        raise SignatureValidationError("Signature image must be valid base64") from exc

    if len(image_bytes) > MAX_SIGNATURE_BYTES:
        raise SignatureValidationError("Signature image is too large")
    if not image_bytes.startswith(PNG_MAGIC):
        raise SignatureValidationError("Signature image must be a PNG file")
    return image_bytes


def validate_signature_image(image_bytes: bytes) -> None:
    pixmap = fitz.Pixmap(image_bytes)
    gray = fitz.Pixmap(fitz.csGRAY, pixmap) if pixmap.n != 1 else pixmap
    try:
        if gray.width < MIN_SIGNATURE_WIDTH or gray.height < MIN_SIGNATURE_HEIGHT:
            raise SignatureValidationError("Signature image is too small")

        ink_pixels = sum(1 for value in gray.samples if value < 250)
        if ink_pixels < MIN_INK_PIXELS:
            raise SignatureValidationError("Signature image appears empty")
    except SignatureValidationError:
        raise
    except Exception as exc:
        raise SignatureValidationError("Signature image is not a valid PNG") from exc
    finally:
        if gray is not pixmap:
            gray = None
        pixmap = None


def save_submission_signature(
    settings: Settings,
    submission_id: UUID,
    image_bytes: bytes,
) -> tuple[str, str, datetime]:
    validate_signature_image(image_bytes)
    settings.ensure_storage_dirs()

    relative_path = f"{settings.signature_storage_dir}/{submission_id}.png"
    absolute_path = settings.storage_root / relative_path
    temp_path = absolute_path.with_suffix(".png.tmp")

    signature_hash = hashlib.sha256(image_bytes).hexdigest()
    signed_at = datetime.now(UTC)

    try:
        temp_path.write_bytes(image_bytes)
        temp_path.replace(absolute_path)
    except OSError as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store signature image",
        ) from exc

    return relative_path, signature_hash, signed_at


def load_submission_signature_bytes(settings: Settings, signature_path: str | None) -> bytes | None:
    if not signature_path:
        return None

    path = Path(signature_path)
    if not path.is_absolute():
        path = settings.storage_root / path
    path = path.resolve()

    if not path.exists():
        return None
    return path.read_bytes()


def parse_and_validate_signature(signature_image_base64: str) -> bytes:
    image_bytes = decode_signature_image(signature_image_base64)
    validate_signature_image(image_bytes)
    return image_bytes
