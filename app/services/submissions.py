from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import SubmissionMode, SubmissionStatus
from app.models.submission import Submission
from app.schemas.submission import GuestSubmissionCreate
from app.services.forms import get_active_form


def get_missing_required_fields(schema_json: dict, payload_json: dict) -> list[str]:
    required = schema_json.get("required", [])
    if not isinstance(required, list):
        return []
    return [field for field in required if isinstance(field, str) and field not in payload_json]


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
    missing_fields = get_missing_required_fields(form.schema_json, data.payload_json)
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required form fields: {', '.join(missing_fields)}",
        )

    sequence_date = get_sequence_date(settings)
    start_number = get_next_start_number(db, sequence_date)

    submission = Submission(
        form_id=form.id,
        form_version=form.version,
        user_id=None,
        filled_for_related_person_id=None,
        mode=SubmissionMode.GUEST,
        participant_role=data.participant_role,
        vehicle_type=data.vehicle_type,
        start_number=start_number,
        sequence_date=sequence_date,
        payload_json=data.payload_json,
        consents_json=data.consents_json,
        declarations_accepted=data.declarations_accepted,
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )
    db.add(submission)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(submission)
    return submission
