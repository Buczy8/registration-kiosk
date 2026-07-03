from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT
from app.models.enums import SubmissionMode
from app.models.submission import Submission
from app.services.pdf_mapping import MANAGED_CHECKBOX_FIELDS, PdfFieldMapping, get_guest_submission_pdf_mapping


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
            elif widget.field_name in MANAGED_CHECKBOX_FIELDS:
                if widget.field_name in mapping.checked_fields:
                    widget.field_value = widget.on_state() or "Yes"
                else:
                    widget.field_value = ""
                widget.update()


def fill_guest_submission_template(submission: Submission) -> bytes:
    if submission.form is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission form not loaded")

    template_path = _resolve_template_path(submission.form.pdf_template_path)
    if not template_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PDF template not found")

    mapping = get_guest_submission_pdf_mapping(submission)
    doc = fitz.open(template_path)
    try:
        if hasattr(doc, "need_appearances"):
            doc.need_appearances(True)
        _write_pdf_fields(doc, mapping)
        return doc.write(garbage=4, deflate=True)
    finally:
        doc.close()


def generate_guest_submission_pdf(db: Session, submission_id: UUID) -> tuple[Submission, bytes]:
    submission = db.execute(select(Submission).where(Submission.id == submission_id)).scalar_one_or_none()
    if submission is None or submission.mode != SubmissionMode.GUEST:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    pdf_bytes = fill_guest_submission_template(submission)
    submission.pdf_path = f"generated://submissions/{submission.id}.pdf"
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission, pdf_bytes
