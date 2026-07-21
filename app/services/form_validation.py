import re
from datetime import date
from fastapi import HTTPException, status
from app.models.enums import ParticipantRole

PESEL_PATTERN = re.compile(r"^\d{11}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def get_missing_required_fields(schema_json: dict, payload_json: dict) -> list[str]:
    required = schema_json.get("required", [])
    if not isinstance(required, list):
        return []
    return [field for field in required if isinstance(field, str) and field not in payload_json]


def validate_required_fields(schema_json: dict, payload_json: dict) -> None:
    missing_fields = get_missing_required_fields(schema_json, payload_json)
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required form fields: {', '.join(missing_fields)}",
        )


def validate_submission_data(
    schema_json: dict,
    payload_json: dict,
    participant_role: ParticipantRole,
) -> None:
    # 1. Check required fields
    validate_required_fields(schema_json, payload_json)

    properties = schema_json.get("properties", {})

    # 2. Email format validation
    email = payload_json.get("email")
    if email:
        email = str(email).strip()
        if not EMAIL_PATTERN.match(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Niepoprawny format adresu e-mail.",
            )

    # 3. Birth date validation
    birth_date = payload_json.get("birth_date")
    if birth_date:
        try:
            date.fromisoformat(str(birth_date).strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Niepoprawny format daty urodzenia (wymagany YYYY-MM-DD).",
            )

    # 4. Identity Document validation (pesel_or_id_card rule)
    if schema_json.get("identity_document_rule") == "pesel_or_id_card":
        pesel = payload_json.get("pesel")
        id_card_series = payload_json.get("id_card_series")
        id_card_number = payload_json.get("id_card_number")

        has_pesel = bool(pesel and str(pesel).strip())
        has_id_card = bool(
            id_card_series and str(id_card_series).strip() and
            id_card_number and str(id_card_number).strip()
        )

        if not (has_pesel or has_id_card):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wymagany jest dokument tożsamości (PESEL lub seria i numer dowodu osobistego).",
            )

        if has_pesel:
            clean_pesel = str(pesel).strip()
            if not PESEL_PATTERN.match(clean_pesel):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PESEL musi składać się z dokładnie 11 cyfr.",
                )

    # 5. Role-Specific Field validation
    if participant_role == ParticipantRole.LEGAL_GUARDIAN:
        # Legal guardian must submit minor details if defined in properties
        for field in ("minor_first_name", "minor_last_name", "guardian_relation"):
            if field in properties:
                val = payload_json.get(field)
                if not (val and str(val).strip()):
                    title = properties.get(field, {}).get("title", field)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Dla opiekuna prawnego wymagane jest podanie pola: {title}.",
                    )

