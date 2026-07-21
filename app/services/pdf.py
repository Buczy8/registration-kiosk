from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
import fitz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.models.submission import Submission
from app.services.pdf_mapping import (
    PdfFieldMapping,
    get_guest_submission_pdf_mapping,
)
from app.services.signatures import load_submission_signature_bytes


def _resolve_template_path(template_path: str) -> Path:
    path = Path(template_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


import os

FONT_POLISH_PATH = r"C:\Users\Paweł Buczek\Downloads\arial\ARIAL.TTF"
FONT_RES_NAME = "ArialUnicodePL"

def _write_pdf_fields(doc: fitz.Document, mapping: PdfFieldMapping) -> None:
    for page in doc:
        for widget in page.widgets() or []:
            if widget.field_name in mapping.text_values:
                val = mapping.text_values[widget.field_name]
                widget.text_font = "notos"
                widget.field_value = val
                widget.update()
            elif widget.field_name in mapping.managed_checkboxes:
                if widget.field_name in mapping.checked_fields:
                    widget.field_value = widget.on_state() or "Yes"
                else:
                    widget.field_value = ""
                widget.update()










def _embed_signature_image(
        doc: fitz.Document,
        submission: Submission,
        settings: Settings | None,
        mapping: PdfFieldMapping,
) -> None:
    if settings is None or not submission.signature_path:
        return

    sig_page = None
    sig_rect = None

    # 1. Try to find the signature widget by its mapped field name
    if mapping.signature_field_name:
        for page_idx, page in enumerate(doc):
            for widget in page.widgets() or []:
                if widget.field_name == mapping.signature_field_name:
                    sig_page = page_idx
                    sig_rect = widget.rect
                    break
            if sig_rect is not None:
                break

    # 2. Fallback to coordinates defined in the mapping
    if sig_page is None or sig_rect is None:
        sig_page = mapping.signature_page
        sig_rect = mapping.signature_rect

    # 3. Fallback to generic auto-detection by name match
    if sig_page is None or sig_rect is None:
        for page_idx, page in enumerate(doc):
            for widget in page.widgets() or []:
                if widget.field_name and (
                    widget.field_name.startswith("signature")
                    or "signature" in widget.field_name.lower()
                ):
                    sig_page = page_idx
                    sig_rect = widget.rect
                    break
            if sig_rect is not None:
                break

    if sig_page is None or sig_rect is None:
        return

    image_bytes = load_submission_signature_bytes(settings, submission.signature_path)
    if not image_bytes:
        return

    if sig_page >= len(doc):
        return

    page = doc[sig_page]
    for widget in list(page.widgets() or []):
        if widget.field_name == mapping.signature_field_name or (
            widget.field_name and "signature" in widget.field_name.lower()
        ):
            page.delete_widget(widget)
    page.insert_image(sig_rect, stream=image_bytes, keep_proportion=True, rotate=page.rotation)




def fill_guest_submission_template(submission: Submission, *, settings: Settings | None = None) -> bytes:
    if submission.form is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission form not loaded")

    template_path = _resolve_template_path(submission.form.pdf_template_path)
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF template not found: {template_path}",
        )

    mapping = get_guest_submission_pdf_mapping(submission)

    with fitz.open(template_path) as doc:
        if hasattr(doc, "need_appearances"):
            doc.need_appearances(True)

        _write_pdf_fields(doc, mapping)
        _embed_signature_image(doc, submission, settings, mapping)
        return doc.write(garbage=4, deflate=True)


async def generate_submission_pdf(db: AsyncSession, submission_id: UUID) -> tuple[Submission, bytes]:
    stmt = (
        select(Submission)
        .options(selectinload(Submission.form))
        .where(Submission.id == submission_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()

    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    settings = get_settings()
    import asyncio
    pdf_bytes = await asyncio.to_thread(
        fill_guest_submission_template, submission, settings=settings
    )
    submission.pdf_path = f"generated://submissions/{submission.id}.pdf"

    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission, pdf_bytes


def render_pdf_to_png(pdf_bytes: bytes, page_index: int = 0, dpi: int = 150) -> bytes:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if page_index < 0 or page_index >= len(doc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strona {page_index} nie istnieje w dokumencie PDF (liczba stron: {len(doc)}).",
            )
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        png_data = pix.tobytes("png")

        # Zapisz kopie roboczą do szybkiego podglądu i weryfikacji
        debug_path = PROJECT_ROOT / "scratch" / "debug_last_png.png"
        debug_path.write_bytes(png_data)

        return png_data








async def generate_submission_png(
    db: AsyncSession, submission_id: UUID, page_index: int = 0, dpi: int = 150
) -> tuple[Submission, bytes]:
    submission, pdf_bytes = await generate_submission_pdf(db=db, submission_id=submission_id)
    png_bytes = await asyncio.to_thread(render_pdf_to_png, pdf_bytes, page_index, dpi)
    return submission, png_bytes

