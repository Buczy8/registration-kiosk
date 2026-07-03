import uuid

from app.models.form import Form
from app.schemas.form import ActiveFormResponse


def _form() -> Form:
    return Form(
        id=uuid.uuid4(),
        code="track-day-waiver",
        name="Track Day Waiver",
        version="1.0",
        schema_json={
            "required": ["first_name", "last_name"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
            },
        },
        pdf_template_path="/templates/track-day-waiver.pdf",
        is_active=True,
    )


def test_active_form_response_serializes_form_model():
    response = ActiveFormResponse.model_validate(_form())
    response_payload = response.model_dump()

    assert response_payload["code"] == "track-day-waiver"
    assert response_payload["name"] == "Track Day Waiver"
    assert response_payload["version"] == "1.0"
    assert response_payload["schema_json"]["required"] == ["first_name", "last_name"]


def test_active_form_response_does_not_expose_pdf_template_path():
    response = ActiveFormResponse.model_validate(_form())

    assert "pdf_template_path" not in response.model_dump()
