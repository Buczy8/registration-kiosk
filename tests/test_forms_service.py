import uuid

import pytest
from fastapi import HTTPException

from app.models.form import Form
from app.services.forms import get_active_form


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, value):
        self._value = value

    def execute(self, _statement):
        return _Result(self._value)


def _form() -> Form:
    return Form(
        id=uuid.uuid4(),
        code="guest-registration",
        name="Rejestracja gościa",
        version="1.0",
        schema_json={"required": ["first_name"]},
        pdf_template_path="templates/forms/guest-registration-v1.pdf",
        is_active=True,
    )


def test_get_active_form_returns_form_when_db_has_one():
    form = _form()

    assert get_active_form(_FakeDb(form)) is form


def test_get_active_form_raises_404_when_db_returns_none():
    with pytest.raises(HTTPException) as exc_info:
        get_active_form(_FakeDb(None))

    assert exc_info.value.status_code == 404
