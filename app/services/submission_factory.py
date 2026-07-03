from datetime import date

from app.models.enums import SubmissionMode, SubmissionStatus
from app.models.form import Form
from app.models.submission import Submission
from app.schemas.submission import GuestSubmissionCreate


def build_guest_submission(
    *,
    form: Form,
    data: GuestSubmissionCreate,
    start_number: int,
    sequence_date: date,
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
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )
