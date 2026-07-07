from fastapi import HTTPException
import pytest

from app.services.form_validation import get_missing_required_fields, validate_required_fields


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
