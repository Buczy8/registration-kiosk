from datetime import date
import uuid

from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.models.form import Form
from app.models.submission import Submission
from app.services.pdf_mapping import get_guest_submission_pdf_mapping


def _submission(
    *,
    participant_role: ParticipantRole = ParticipantRole.DRIVER,
    vehicle_type: VehicleType = VehicleType.CAR,
    payload_json: dict | None = None,
    consents_json: dict | None = None,
) -> Submission:
    form_schema = {
        "pdf_mapping": {
            "text_fields": {
                "text_10hcx": "{full_name}",
                "text_11neet": "{identity_document}",
                "text_17mtbv": "{start_number}",
                "text_18dulx": "{vehicle_brand_model}",
            },
            "checkboxes": {
                "participant_role": {
                    "driver": "checkbox_1yrvm",
                    "legal_guardian": "checkbox_4bnfu"
                },
                "vehicle_type": {
                    "car": "checkbox_7agj"
                },
                "guardian_relation": {
                    "parent": "checkbox_20ajne"
                }
            },
            "consents": {
                "image_publication": "checkbox_24iihx"
            }
        }
    }

    form = Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json=form_schema,
        pdf_template_path="templates/forms/guest-registration-v1.pdf",
        is_active=True,
    )
    return Submission(
        id=uuid.uuid4(),
        form_id=form.id,
        form=form,
        form_version=form.version,
        user_id=None,
        filled_for_related_person_id=None,
        mode=SubmissionMode.GUEST,
        participant_role=participant_role,
        vehicle_type=vehicle_type,
        start_number=77,
        sequence_date=date(2026, 7, 3),
        payload_json=payload_json or {},
        consents_json=consents_json or {},
        declarations_accepted=True,
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )


def test_get_guest_submission_pdf_mapping_builds_text_and_checkbox_fields():
    mapping = get_guest_submission_pdf_mapping(
        _submission(
            payload_json={
                "first_name": "Jan",
                "last_name": "Kowalski",
                "pesel": "90010112345",
                "vehicle_brand": "BMW",
                "vehicle_model": "M3",
                "signature_place": "Biłgoraj, 03.07.2026",
            },
            consents_json={"privacy": True, "image_publication": True},
        )
    )

    assert mapping.text_values["text_10hcx"] == "Jan Kowalski"
    assert mapping.text_values["text_11neet"] == "90010112345"
    assert mapping.text_values["text_17mtbv"] == "77"
    assert mapping.text_values["text_18dulx"] == "BMW M3"
    assert "checkbox_1yrvm" in mapping.checked_fields
    assert "checkbox_7agj" in mapping.checked_fields
    assert "checkbox_24iihx" in mapping.checked_fields


def test_get_guest_submission_pdf_mapping_maps_guardian_relation():
    guardian_mapping = get_guest_submission_pdf_mapping(
        _submission(
            participant_role=ParticipantRole.LEGAL_GUARDIAN,
            payload_json={"guardian_relation": "parent"},
        )
    )
    assert "checkbox_20ajne" in guardian_mapping.checked_fields

    empty_mapping = get_guest_submission_pdf_mapping(
        _submission(
            participant_role=ParticipantRole.DRIVER,
            payload_json={},
        )
    )
    assert "checkbox_20ajne" not in empty_mapping.checked_fields