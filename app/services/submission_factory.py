from datetime import date, datetime
from uuid import UUID

from app.models.enums import SubmissionMode, SubmissionStatus
from app.models.form import Form
from app.models.submission import Submission
from app.schemas.submission import AccountSubmissionCreate, GuestSubmissionCreate


def build_guest_submission(
    *,
    form: Form,
    data: GuestSubmissionCreate,
    start_number: int,
    sequence_date: date,
    signature_path: str | None = None,
    signature_hash: str | None = None,
    signed_at: datetime | None = None,
) -> Submission:
    return Submission(
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
        signature_path=signature_path,
        signature_hash=signature_hash,
        signed_at=signed_at,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )


def build_account_submission(
    *,
    form: Form,
    data: AccountSubmissionCreate,
    user_id: UUID,
    start_number: int,
    sequence_date: date,
    signature_path: str | None = None,
    signature_hash: str | None = None,
    signed_at: datetime | None = None,
) -> Submission:
    return Submission(
        form_id=form.id,
        form_version=form.version,
        user_id=user_id,
        filled_for_related_person_id=None,
        mode=SubmissionMode.ACCOUNT,
        participant_role=data.participant_role,
        vehicle_type=data.vehicle_type,
        start_number=start_number,
        sequence_date=sequence_date,
        payload_json=data.payload_json,
        consents_json=data.consents_json,
        declarations_accepted=data.declarations_accepted,
        signature_path=signature_path,
        signature_hash=signature_hash,
        signed_at=signed_at,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )
