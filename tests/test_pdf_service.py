from datetime import date
import uuid

import fitz

from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.models.form import Form
from app.models.submission import Submission
from app.services.pdf import fill_guest_submission_template


def _template_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    for field_name, rect, field_type in [
        ("checkbox_19pppm", fitz.Rect(90, 10, 100, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_20jfuy", fitz.Rect(110, 10, 120, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_21iohl", fitz.Rect(130, 10, 140, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_26aqhm", fitz.Rect(10, 10, 20, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_29pnyu", fitz.Rect(30, 10, 40, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_22zynj", fitz.Rect(50, 10, 60, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("checkbox_23dbga", fitz.Rect(70, 10, 80, 20), fitz.PDF_WIDGET_TYPE_CHECKBOX),
        ("text_8fpaj", fitz.Rect(10, 40, 180, 60), fitz.PDF_WIDGET_TYPE_TEXT),
        ("text_9yvjs", fitz.Rect(10, 70, 180, 90), fitz.PDF_WIDGET_TYPE_TEXT),
        ("text_15qcfa", fitz.Rect(10, 100, 180, 120), fitz.PDF_WIDGET_TYPE_TEXT),
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
        schema_json={},
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
    assert values["text_8fpaj"] == "Jan Kowalski"
    assert values["text_9yvjs"] == "90010112345"
    assert values["text_15qcfa"] == "77"
    assert values["checkbox_26aqhm"] == "Yes"
    assert values["checkbox_29pnyu"] == "Yes"
    assert values["checkbox_22zynj"] in ("", "Off")
    assert values["checkbox_23dbga"] == "Yes"


def test_fill_guest_submission_template_does_not_check_guardian_for_driver(tmp_path):
    template_path = tmp_path / "guest-registration.pdf"
    _template_pdf(template_path)
    form = Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json={},
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
            "guardian_relation": "parent",
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

    assert values["checkbox_19pppm"] in ("", "Off")
    assert values["checkbox_20jfuy"] in ("", "Off")
    assert values["checkbox_21iohl"] in ("", "Off")
