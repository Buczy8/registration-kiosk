from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType


class SubmissionCreate(BaseModel):
    participant_role: ParticipantRole
    vehicle_type: VehicleType
    payload_json: dict[str, Any] = Field(min_length=1)
    consents_json: dict[str, Any] = Field(min_length=1)
    declarations_accepted: bool
    signature_image_base64: str = Field(min_length=1)

    @field_validator("declarations_accepted")
    @classmethod
    def declarations_must_be_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Declarations must be accepted")
        return value


class GuestSubmissionCreate(SubmissionCreate):
    pass


class GuestSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    form_id: UUID
    form_version: str
    mode: SubmissionMode
    participant_role: ParticipantRole
    vehicle_type: VehicleType
    start_number: int
    sequence_date: date
    status: SubmissionStatus


class AccountSubmissionCreate(SubmissionCreate):
    pass


class AccountSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    form_id: UUID
    form_version: str
    mode: SubmissionMode
    participant_role: ParticipantRole
    vehicle_type: VehicleType
    start_number: int
    sequence_date: date
    status: SubmissionStatus
