from fastapi import HTTPException
import pytest

from app.services.form_validation import (
    get_missing_required_fields,
    validate_required_fields,
    validate_submission_data,
)
from app.models.enums import ParticipantRole


def test_get_missing_required_fields_returns_missing_string_fields():
    missing = get_missing_required_fields(
        {"required": ["first_name", "last_name", "birth_date"]},
        {"first_name": "Jan"},
    )

    assert missing == ["last_name", "birth_date"]


def test_get_missing_required_fields_ignores_invalid_required_entries():
    missing = get_missing_required_fields(
        {"required": ["first_name", 123, None]},
        {},
    )

    assert missing == ["first_name"]


def test_validate_required_fields_raises_bad_request_with_missing_fields():
    with pytest.raises(HTTPException) as exc_info:
        validate_required_fields(
            {"required": ["first_name", "last_name"]},
            {"first_name": "Jan"},
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Missing required form fields: last_name"


def test_validate_submission_data_valid_payload():
    schema = {
        "required": ["first_name"],
        "identity_document_rule": "pesel_or_id_card",
        "properties": {
            "first_name": {"title": "Imię"},
            "pesel": {"title": "PESEL"},
        }
    }
    payload = {
        "first_name": "Jan",
        "email": "jan@example.com",
        "birth_date": "1990-01-01",
        "pesel": "12345678901",
    }
    # Should not raise exception
    validate_submission_data(schema, payload, ParticipantRole.PASSENGER)


def test_validate_submission_data_invalid_email():
    schema = {"required": ["first_name"]}
    payload = {"first_name": "Jan", "email": "invalid_email"}
    with pytest.raises(HTTPException) as exc_info:
        validate_submission_data(schema, payload, ParticipantRole.PASSENGER)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Niepoprawny format adresu e-mail."


def test_validate_submission_data_invalid_date():
    schema = {"required": ["first_name"]}
    payload = {"first_name": "Jan", "birth_date": "1990/01/01"}
    with pytest.raises(HTTPException) as exc_info:
        validate_submission_data(schema, payload, ParticipantRole.PASSENGER)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Niepoprawny format daty urodzenia (wymagany YYYY-MM-DD)."


def test_validate_submission_data_missing_identity():
    schema = {"required": [], "identity_document_rule": "pesel_or_id_card"}
    payload = {}
    with pytest.raises(HTTPException) as exc_info:
        validate_submission_data(schema, payload, ParticipantRole.PASSENGER)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Wymagany jest dokument tożsamości (PESEL lub seria i numer dowodu osobistego)."


def test_validate_submission_data_invalid_pesel():
    schema = {"required": [], "identity_document_rule": "pesel_or_id_card"}
    payload = {"pesel": "123"}
    with pytest.raises(HTTPException) as exc_info:
        validate_submission_data(schema, payload, ParticipantRole.PASSENGER)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "PESEL musi składać się z dokładnie 11 cyfr."


def test_validate_submission_data_valid_id_card():
    schema = {"required": [], "identity_document_rule": "pesel_or_id_card"}
    payload = {"id_card_series": "ABC", "id_card_number": "123456"}
    # Should not raise exception
    validate_submission_data(schema, payload, ParticipantRole.PASSENGER)


def test_validate_submission_data_driver_missing_vehicle():
    schema = {
        "required": [],
        "properties": {
            "vehicle_brand": {"title": "Marka pojazdu"},
            "vehicle_model": {"title": "Model pojazdu"},
            "vehicle_registration_number": {"title": "Numer rejestracyjny"},
        }
    }
    # If vehicle fields are missing, it should pass because they are optional
    payload = {"vehicle_brand": "BMW", "vehicle_model": "3 Series"}
    validate_submission_data(schema, payload, ParticipantRole.DRIVER)

    payload_empty = {}
    validate_submission_data(schema, payload_empty, ParticipantRole.DRIVER)


def test_validate_submission_data_guardian_missing_minor():
    schema = {
        "required": [],
        "properties": {
            "minor_first_name": {"title": "Imię podopiecznego"},
        }
    }
    payload = {}
    with pytest.raises(HTTPException) as exc_info:
        validate_submission_data(schema, payload, ParticipantRole.LEGAL_GUARDIAN)
    assert exc_info.value.status_code == 400
    assert "Dla opiekuna prawnego wymagane jest podanie pola: Imię podopiecznego." in exc_info.value.detail
