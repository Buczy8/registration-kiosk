from __future__ import annotations

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


def _write_pdf_fields(doc: fitz.Document, mapping: PdfFieldMapping) -> None:
    for page in doc:
        for widget in page.widgets() or []:
            if widget.field_name in mapping.text_values:
                widget.field_value = mapping.text_values[widget.field_name]
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

    if mapping.signature_page is None or mapping.signature_rect is None:
        return

    image_bytes = load_submission_signature_bytes(settings, submission.signature_path)
    if not image_bytes:
        return

    if mapping.signature_page >= len(doc):
        return

    page = doc[mapping.signature_page]
    page.insert_image(mapping.signature_rect, stream=image_bytes, keep_proportion=True)


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
    pdf_bytes = fill_guest_submission_template(submission, settings=settings)
    submission.pdf_path = f"generated://submissions/{submission.id}.pdf"

    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission, pdf_bytes
