from datetime import date
import uuid

import fitz

from app.core.config import Settings
from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.models.form import Form
from app.models.submission import Submission
from app.services.pdf import fill_guest_submission_template
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN
from tests.fixtures.signature_samples import sample_signature_png

MOCK_SCHEMA_JSON = {
    "pdf_mapping": {
        "signature": {
            "page": 0,
            "rect": [610, 500, 740, 536]
        },
        "text_fields": {
            "text_10hcx": "{full_name}",
            "text_11neet": "{identity_document}",
            "text_17mtbv": "{start_number}"
        },
        "checkboxes": {
            "participant_role": {
                "driver": "checkbox_1yrvm",
                "passenger": "checkbox_2vwba",
                "legal_guardian": "checkbox_4bnfu"
            },
            "vehicle_type": {
                "car": "checkbox_7agj"
            },
            "guardian_relation": {
                "parent": "checkbox_20ajne",
                "guardian": "checkbox_21fphh",
                "authorized_person": "checkbox_22xper"
            }
        },
        "consents": {
            "image_publication": "checkbox_24iihx"
        }
    }
}


def _template_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    for field_name, rect, field_type in [
        ("checkbox_20ajne", fitz.Rect(90, 10, 100, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_21fphh", fitz.Rect(110, 10, 120, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_22xper", fitz.Rect(130, 10, 140, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_1yrvm", fitz.Rect(10, 10, 20, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_7agj", fitz.Rect(30, 10, 40, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_24iihx", fitz.Rect(70, 10, 80, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("text_10hcx", fitz.Rect(10, 40, 180, 60), fitz.PDF_WIDGET_TYPE_TEXT),
        ("text_11neet", fitz.Rect(10, 70, 180, 90), fitz.PDF_WIDGET_TYPE_TEXT),
        ("text_17mtbv", fitz.Rect(10, 100, 180, 120), fitz.PDF_WIDGET_TYPE_TEXT),
    ]:
        widget = fitz.Widget()
        widget.field_name = field_name
        widget.field_type = field_type
        widget.rect = rect
        page.add_widget(widget)
    doc.save(path)
    doc.close()


def test_fill_guest_submission_template_fills_interactive_pdf_fields(tmp_path):
    template_path = tmp_path / "guest-registration.pdf"
    _template_pdf(template_path)
    form = Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json=MOCK_SCHEMA_JSON,
        pdf_template_path=str(template_path),
        is_active=True,
    )
    submission = Submission(
        id=uuid.uuid4(),
        form_id=form.id,
        form=form,
        form_version=form.version,
        user_id=None,
        filled_for_related_person_id=None,
        mode=SubmissionMode.GUEST,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=77,
        sequence_date=date(2026, 7, 3),
        payload_json={
            "first_name": "Jan",
            "last_name": "Kowalski",
            "pesel": "90010112345",
        },
        consents_json={"privacy": False, "image_publication": True},
        declarations_accepted=True,
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )

    pdf_bytes = fill_guest_submission_template(submission)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    values = {
        widget.field_name: widget.field_value
        for page in doc
        for widget in (page.widgets() or [])
    }
    doc.close()
    assert values["text_10hcx"] == "Jan Kowalski"
    assert values["text_11neet"] == "90010112345"
    assert values["text_17mtbv"] == "77"
    assert values["checkbox_1yrvm"] == "Yes"
    assert values["checkbox_7agj"] == "Yes"
    assert values["checkbox_24iihx"] == "Yes"


def test_fill_guest_submission_template_does_not_check_guardian_for_driver(tmp_path):
    template_path = tmp_path / "guest-registration.pdf"
    _template_pdf(template_path)
    form = Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json=MOCK_SCHEMA_JSON,  # Przekazujemy konfigurację
        pdf_template_path=str(template_path),
        is_active=True,
    )
    submission = Submission(
        id=uuid.uuid4(),
        form_id=form.id,
        form=form,
        form_version=form.version,
        user_id=None,
        filled_for_related_person_id=None,
        mode=SubmissionMode.GUEST,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=12,
        sequence_date=date(2026, 7, 3),
        payload_json={
            "first_name": "Jan",
            "last_name": "Kowalski",
        },
        consents_json={"privacy": True},
        declarations_accepted=True,
        signature_path=None,
        signature_hash=None,
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )

    pdf_bytes = fill_guest_submission_template(submission)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    values = {
        widget.field_name: widget.field_value
        for page in doc
        for widget in (page.widgets() or [])
    }
    doc.close()

    assert values["checkbox_20ajne"] in ("", "Off")
    assert values["checkbox_21fphh"] in ("", "Off")
    assert values["checkbox_22xper"] in ("", "Off")


def test_fill_guest_submission_template_embeds_signature_image(tmp_path):
    template_path = tmp_path / "guest-registration.pdf"
    _template_pdf(template_path)
    form = Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json=MOCK_SCHEMA_JSON,
        pdf_template_path=str(template_path),
        is_active=True,
    )
    signature_path = tmp_path / "signatures" / "submission.png"
    signature_path.parent.mkdir(parents=True)
    signature_bytes = sample_signature_png()
    signature_path.write_bytes(signature_bytes)
    submission = Submission(
        id=uuid.uuid4(),
        form_id=form.id,
        form=form,
        form_version=form.version,
        user_id=None,
        filled_for_related_person_id=None,
        mode=SubmissionMode.GUEST,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=12,
        sequence_date=date(2026, 7, 3),
        payload_json={"first_name": "Jan", "last_name": "Kowalski"},
        consents_json={"privacy": True},
        declarations_accepted=True,
        signature_path="signatures/submission.png",
        signature_hash="hash",
        signed_at=None,
        pdf_path=None,
        status=SubmissionStatus.SUBMITTED,
    )
    settings = Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        storage_root=tmp_path,
    )

    pdf_bytes = fill_guest_submission_template(submission, settings=settings)

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = document[0].get_images(full=True)
    document.close()
    assert images