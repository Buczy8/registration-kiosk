import uuid
from pathlib import Path

import fitz
import pytest

from app.core.config import Settings
from app.services.signatures import (
    SignatureValidationError,
    decode_signature_image,
    load_submission_signature_bytes,
    parse_and_validate_signature,
    save_submission_signature,
    validate_signature_image,
)
from tests.signature_samples import sample_signature_base64, sample_signature_png


def test_decode_signature_image_accepts_raw_base64():
    image_bytes = decode_signature_image(sample_signature_base64())
    assert image_bytes.startswith(b"\x89PNG")


def test_decode_signature_image_accepts_data_url():
    image_bytes = decode_signature_image(f"data:image/png;base64,{sample_signature_base64()}")
    assert image_bytes.startswith(b"\x89PNG")


def test_validate_signature_image_rejects_empty_canvas():
    document = fitz.open()
    page = document.new_page(width=300, height=120)
    pixmap = page.get_pixmap()
    blank_png = pixmap.tobytes("png")

    with pytest.raises(SignatureValidationError, match="empty"):
        validate_signature_image(blank_png)


def test_save_submission_signature_writes_file(tmp_path: Path):
    settings = Settings(
        kiosk_token="test-kiosk-token-16c",
        jwt_secret_key="test-jwt-secret-key-min-32-chars-long",
        storage_root=tmp_path,
    )
    submission_id = uuid.uuid4()
    image_bytes = sample_signature_png()

    relative_path, signature_hash, signed_at = save_submission_signature(
        settings,
        submission_id,
        image_bytes,
    )

    assert relative_path == f"signatures/{submission_id}.png"
    assert len(signature_hash) == 64
    assert signed_at is not None
    assert (tmp_path / relative_path).exists()
    assert load_submission_signature_bytes(settings, relative_path) == image_bytes


def test_parse_and_validate_signature_returns_bytes():
    image_bytes = parse_and_validate_signature(sample_signature_base64())
    assert image_bytes.startswith(b"\x89PNG")
