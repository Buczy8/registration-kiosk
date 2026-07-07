from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ParticipantRole, VehicleType


class VehicleData(BaseModel):
    brand_model: str = Field(min_length=1)
    registration_number: str = Field(min_length=1)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    user_id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

    address: str | None = None
    birth_date: date | None = None
    document_number: str | None = None
    ice_name: str | None = None
    ice_phone: str | None = None

    vehicles: dict[str, VehicleData] = Field(
        default_factory=dict,
        validation_alias="vehicles_json",
        serialization_alias="vehicles_json",
    )

    @field_validator("vehicles", mode="before")
    @classmethod
    def _coerce_vehicles(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        raise TypeError("vehicles_json must be a dict")


class FormPrefillResponse(BaseModel):
    """
    Prefill danych do formularza (konto): osobowe + dane pojazdu + rola/typ pojazdu.
    """

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None

    address: str | None = None
    birth_date: date | None = None
    document_number: str | None = None

    participant_role: ParticipantRole
    vehicle_type: VehicleType
    vehicle: VehicleData | None = None

