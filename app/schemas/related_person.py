from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ParticipantRole, VehicleType


GUARDIAN_RELATION_VALUES = {"parent", "guardian", "authorized_person"}


class PersonName(BaseModel):
    """Value object: imię i nazwisko podopiecznego"""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class RelatedPersonCreate(BaseModel):
    """Agregat root: dane do utworzenia podopiecznego"""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    guardian_relation: str = Field(min_length=1, max_length=32)
    image_publication_consent: bool
    vehicle_type: VehicleType
    vehicle_brand: str | None = Field(default=None, max_length=120)
    vehicle_model: str | None = Field(default=None, max_length=120)
    vehicle_registration_number: str | None = Field(default=None, max_length=20)

    @field_validator("birth_date")
    @classmethod
    def birth_date_not_future(cls, value: date | None) -> date | None:
        if value is not None:
            today = date.today()
            if value > today:
                raise ValueError("Birth date cannot be in the future")
        return value

    @field_validator("guardian_relation")
    @classmethod
    def guardian_relation_must_be_known(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in GUARDIAN_RELATION_VALUES:
            raise ValueError("guardian_relation must be one of: parent, guardian, authorized_person")
        return normalized

    @field_validator("vehicle_brand", "vehicle_model", "vehicle_registration_number")
    @classmethod
    def blank_vehicle_data_as_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("image_publication_consent")
    @classmethod
    def image_publication_consent_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Image publication consent must be accepted")
        return value


class RelatedPersonResponse(BaseModel):
    """Agregat root: podopieczny w odpowiedzi"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    guardian_relation: str | None
    image_publication_consent: bool
    vehicle_type: VehicleType | None
    vehicle_brand: str | None
    vehicle_model: str | None
    vehicle_registration_number: str | None
    created_at: datetime
    updated_at: datetime


class FormPreview(BaseModel):
    """Value object: podgląd ostatniego formularza podopiecznego"""

    submission_id: UUID
    start_number: int
    participant_role: ParticipantRole
    vehicle_type: VehicleType
    signed_at: datetime | None


class RelatedPersonWithPreview(RelatedPersonResponse):
    """Agregat root z ostatnim formularzem (dla listy podopiecznych)"""

    last_form_preview: FormPreview | None = None
