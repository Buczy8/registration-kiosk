import uuid
from datetime import date

from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.models.form import Form
from app.schemas.submission import GuestSubmissionCreate
from app.services.submission_factory import build_guest_submission


def test_build_guest_submission_populates_guest_submission_fields():
    form = Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json={"required": ["first_name"]},
        pdf_template_path="templates/forms/guest-registration-v1.pdf",
        is_active=True,
    )
    data = GuestSubmissionCreate(
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        payload_json={"first_name": "Jan"},
        consents_json={"privacy": True},
        declarations_accepted=True,
    )

    submission = build_guest_submission(
        form=form,
        data=data,
        start_number=7,
        sequence_date=date(2026, 7, 3),
    )

    assert submission.form_id == form.id
    assert submission.form_version == "1.0"
    assert submission.mode == SubmissionMode.GUEST
    assert submission.participant_role == ParticipantRole.DRIVER
    assert submission.vehicle_type == VehicleType.CAR
    assert submission.start_number == 7
    assert submission.sequence_date == date(2026, 7, 3)
    assert submission.payload_json == {"first_name": "Jan"}
    assert submission.consents_json == {"privacy": True}
    assert submission.declarations_accepted is True
    assert submission.status == SubmissionStatus.SUBMITTED
    assert submission.user_id is None
    assert submission.filled_for_related_person_id is None
