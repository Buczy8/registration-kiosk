from dataclasses import dataclass

import fitz

from app.models.enums import ParticipantRole
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
PRIVACY_CONSENT_FIELD = "checkbox_22zynj"
IMAGE_PUBLICATION_CONSENT_FIELD = "checkbox_23dbga"
SIGNATURE_PDF_PAGE = 0
# Szablon: documentation/Uniwersalne Oświadczenie Uczestnika... (strona 792x612 pt, pozioma).
# Pole text_24wgja (data i miejscowość): Rect(413, 497, 537, 507), linia pod spodem y=508.5.
# Podpis: linia x=597..719, y=508.5, etykieta "Czytelny Podpis Uczestnika / Opiekuna" pod linią.
SIGNATURE_PDF_RECT = fitz.Rect(597, 476, 719, 507)
MANAGED_CHECKBOX_FIELDS = {
    *ROLE_FIELDS.values(),
    *VEHICLE_FIELDS.values(),
    *GUARDIAN_RELATION_FIELDS.values(),
    PRIVACY_CONSENT_FIELD,
    IMAGE_PUBLICATION_CONSENT_FIELD,
}


@dataclass(frozen=True)
class PdfFieldMapping:
    text_values: dict[str, str]
    checked_fields: set[str]


def _join_present(*values: object, separator: str = " ") -> str:
    return separator.join(str(value).strip() for value in values if str(value or "").strip())


def _identity_document(payload: dict) -> str:
    if payload.get("pesel"):
        return str(payload["pesel"])
    return _join_present(payload.get("id_card_series"), payload.get("id_card_number"))


def get_guest_submission_pdf_mapping(submission: Submission) -> PdfFieldMapping:
    payload = submission.payload_json or {}
    consents = submission.consents_json or {}
    checked_fields = {
        ROLE_FIELDS[submission.participant_role.value],
        VEHICLE_FIELDS[submission.vehicle_type.value],
    }
    if submission.participant_role == ParticipantRole.LEGAL_GUARDIAN:
        guardian_relation = payload.get("guardian_relation")
        if guardian_relation in GUARDIAN_RELATION_FIELDS:
            checked_fields.add(GUARDIAN_RELATION_FIELDS[guardian_relation])
    if consents.get("privacy"):
        checked_fields.add(PRIVACY_CONSENT_FIELD)
    if consents.get("image_publication") or consents.get("media") or consents.get("marketing"):
        checked_fields.add(IMAGE_PUBLICATION_CONSENT_FIELD)

    return PdfFieldMapping(
        text_values={
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
        checked_fields=checked_fields,
    )
