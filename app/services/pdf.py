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


ROLE_FIELDS = {
    "driver": "checkbox_26aqhm",
    "passenger": "checkbox_3klde",
    "legal_guardian": "checkbox_27ywf",
}
VEHICLE_FIELDS = {
    "car": "checkbox_29pnyu",
    "motorcycle": "checkbox_25ahnh",
    "gokart": "checkbox_30txms",
}
GUARDIAN_RELATION_FIELDS = {
    "parent": "checkbox_19pppm",
    "guardian": "checkbox_20jfuy",
    "authorized_person": "checkbox_21iohl",
}


def _resolve_template_path(template_path: str) -> Path:
    path = Path(template_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _join_present(*values: object, separator: str = " ") -> str:
    return separator.join(str(value).strip() for value in values if str(value or "").strip())


def _identity_document(payload: dict) -> str:
    if payload.get("pesel"):
        return str(payload["pesel"])
    return _join_present(payload.get("id_card_series"), payload.get("id_card_number"))


def _guest_template_values(submission: Submission) -> tuple[dict[str, str], set[str]]:
    payload = submission.payload_json or {}
    consents = submission.consents_json or {}
    checked_fields = {
        ROLE_FIELDS[submission.participant_role.value],
        VEHICLE_FIELDS[submission.vehicle_type.value],
    }
    guardian_relation = payload.get("guardian_relation")
    if guardian_relation in GUARDIAN_RELATION_FIELDS:
        checked_fields.add(GUARDIAN_RELATION_FIELDS[guardian_relation])
    if consents.get("privacy"):
        checked_fields.add("checkbox_22zynj")
    if consents.get("image_publication") or consents.get("media") or consents.get("marketing"):
        checked_fields.add("checkbox_23dbga")

    return (
        {
            "text_8fpaj": _join_present(payload.get("first_name"), payload.get("last_name")),
            "text_9yvjs": _identity_document(payload),
            "text_10oepk": str(payload.get("residence_address") or ""),
            "text_11nkcj": str(payload.get("birth_date") or ""),
            "text_12fueu": str(payload.get("phone") or ""),
            "text_13ywdm": str(payload.get("email") or ""),
            "text_14ofnm": _join_present(
                payload.get("emergency_contact_name"),
                payload.get("emergency_contact_phone"),
                separator=", ",
            ),
            "text_15qcfa": str(submission.start_number),
            "text_16ulhc": _join_present(payload.get("vehicle_brand"), payload.get("vehicle_model")),
            "text_17bbxm": str(payload.get("vehicle_registration_number") or ""),
            "text_18lzou": _join_present(payload.get("minor_first_name"), payload.get("minor_last_name")),
            "text_24wgja": str(payload.get("signature_place") or submission.sequence_date.isoformat()),
        },
        checked_fields,
    )


def fill_guest_submission_template(submission: Submission) -> bytes:
    if submission.form is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission form not loaded")

    template_path = _resolve_template_path(submission.form.pdf_template_path)
    if not template_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PDF template not found")

    text_values, checked_fields = _guest_template_values(submission)
    doc = fitz.open(template_path)
    try:
        if hasattr(doc, "need_appearances"):
            doc.need_appearances(True)
        for page in doc:
            for widget in page.widgets() or []:
                if widget.field_name in text_values:
                    widget.field_value = text_values[widget.field_name]
                    widget.update()
                elif widget.field_name in checked_fields:
                    widget.field_value = widget.on_state() or "Yes"
                    widget.update()
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
