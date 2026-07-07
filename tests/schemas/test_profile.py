from datetime import date
from uuid import uuid4

from app.models.enums import ParticipantRole, VehicleType
from app.schemas.profile import FormPrefillResponse, ProfileResponse, VehicleData


def test_vehicle_data_requires_fields():
    v = VehicleData(brand_model="BMW M3", registration_number="WX 12345")
    assert v.brand_model == "BMW M3"


def test_profile_response_serializes_vehicles_json_alias():
    user_id = uuid4()
    payload = ProfileResponse(
        user_id=user_id,
        email="jan.kowalski@example.com",
        first_name="Jan",
        last_name="Kowalski",
        vehicles_json={
            "primary": {"brand_model": "BMW M3", "registration_number": "WX 12345"},
        },
    ).model_dump(by_alias=True)

    assert payload["user_id"] == user_id
    assert "vehicles_json" in payload
    assert payload["vehicles_json"]["primary"]["brand_model"] == "BMW M3"


def test_form_prefill_response_accepts_personal_and_vehicle_fields():
    data = FormPrefillResponse(
        first_name="Jan",
        last_name="Kowalski",
        email="jan.kowalski@example.com",
        phone="+48 500 600 700",
        address="Warszawa",
        birth_date=date(1990, 1, 1),
        document_number="ABC123",
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        vehicle=VehicleData(brand_model="BMW M3", registration_number="WX 12345"),
    )

    assert data.participant_role == ParticipantRole.DRIVER
    assert data.vehicle_type == VehicleType.CAR

