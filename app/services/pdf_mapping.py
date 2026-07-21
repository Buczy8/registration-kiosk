from dataclasses import dataclass

import fitz

from app.models.enums import ParticipantRole
from app.models.submission import Submission


@dataclass(frozen=True)
class PdfFieldMapping:
    text_values: dict[str, str]
    checked_fields: set[str]
    managed_checkboxes: set[str]
    signature_page: int | None
    signature_rect: fitz.Rect | None
    signature_field_name: str | None = None


class SafePayload(dict):
    def __missing__(self, key):
        return ""


def _join_non_empty(*parts: str | None, sep: str = " ") -> str:
    return sep.join(str(part).strip() for part in parts if part and str(part).strip())


def get_guest_submission_pdf_mapping(submission: Submission) -> PdfFieldMapping:
    form_schema = submission.form.schema_json if submission.form else {}
    pdf_mapping = form_schema.get("pdf_mapping", {})

    text_mapping = pdf_mapping.get("text_fields", {})
    checkbox_mapping = pdf_mapping.get("checkboxes", {})
    consent_mapping = pdf_mapping.get("consents", {})
    sig_mapping = pdf_mapping.get("signature", {})

    payload = submission.payload_json or {}
    consents = submission.consents_json or {}

    context = {
        **payload,
        "start_number": str(submission.start_number),
        "sequence_date": submission.sequence_date.isoformat(),
        "participant_role": submission.participant_role.value if submission.participant_role else "",
        "vehicle_type": submission.vehicle_type.value if submission.vehicle_type else "",
    }
    context["full_name"] = _join_non_empty(payload.get("first_name"), payload.get("last_name"))
    context["identity_document"] = (
        payload.get("pesel")
        or _join_non_empty(payload.get("id_card_series"), payload.get("id_card_number"))
    )
    context["emergency_contact"] = _join_non_empty(
        payload.get("emergency_contact_name"),
        payload.get("emergency_contact_phone"),
        sep=", ",
    )
    context["minor_full_name"] = _join_non_empty(
        payload.get("minor_first_name"),
        payload.get("minor_last_name"),
    )
    context["vehicle_brand_model"] = (
        payload.get("vehicle_brand_model")
        or _join_non_empty(payload.get("vehicle_brand"), payload.get("vehicle_model"))
    )
    if not context.get("signature_place"):
        context["signature_place"] = submission.sequence_date.isoformat()
        
    cleaned_context = {k: (v if v is not None else "") for k, v in context.items()}
    safe_context = SafePayload(cleaned_context)

    text_values = {
        pdf_field: template.format_map(safe_context).strip()
        for pdf_field, template in text_mapping.items()
    }

    checked_fields = set()
    managed_checkboxes = set()

    for field_name, options_map in checkbox_mapping.items():
        managed_checkboxes.update(options_map.values())
        val = context.get(field_name)
        if val and val in options_map:
            checked_fields.add(options_map[val])

    for consent_key, pdf_checkbox in consent_mapping.items():
        managed_checkboxes.add(pdf_checkbox)
        if consents.get(consent_key):
            checked_fields.add(pdf_checkbox)

    sig_page = None
    sig_rect = None
    sig_field_name = None

    if isinstance(sig_mapping, str):
        sig_field_name = sig_mapping
    elif isinstance(sig_mapping, dict):
        sig_page = sig_mapping.get("page")
        sig_rect_coords = sig_mapping.get("rect")
        sig_rect = fitz.Rect(*sig_rect_coords) if sig_rect_coords else None

    return PdfFieldMapping(
        text_values=text_values,
        checked_fields=checked_fields,
        managed_checkboxes=managed_checkboxes,
        signature_page=sig_page,
        signature_rect=sig_rect,
        signature_field_name=sig_field_name,
    )