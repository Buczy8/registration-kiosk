from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.submission import Submission
from app.schemas.submission import GuestSubmissionCreate
from app.services.form_validation import get_missing_required_fields, validate_required_fields
from app.services.forms import get_active_form
from app.services.signatures import SignatureValidationError, parse_and_validate_signature, save_submission_signature
from app.services.submission_factory import build_guest_submission


def get_sequence_date(settings: Settings) -> date:
    return datetime.now(ZoneInfo(settings.start_number_timezone)).date()


def get_next_start_number(db: Session, sequence_date: date) -> int:
    return int(
        db.execute(
            text("SELECT next_start_number(:sequence_date)"),
            {"sequence_date": sequence_date},
        ).scalar_one()
    )


def create_guest_submission(
    db: Session,
    data: GuestSubmissionCreate,
    settings: Settings,
) -> Submission:
    form = get_active_form(db)
    validate_required_fields(form.schema_json, data.payload_json)

    try:
        image_bytes = parse_and_validate_signature(data.signature_image_base64)
    except SignatureValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    sequence_date = get_sequence_date(settings)
    start_number = get_next_start_number(db, sequence_date)

    submission = build_guest_submission(
        form=form,
        data=data,
        start_number=start_number,
        sequence_date=sequence_date,
    )
    db.add(submission)
    try:
        db.flush()
        signature_path, signature_hash, signed_at = save_submission_signature(
            settings,
            submission.id,
            image_bytes,
        )
        submission.signature_path = signature_path
        submission.signature_hash = signature_hash
        submission.signed_at = signed_at
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(submission)
    return submission
