from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActiveFormResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: UUID
    code: str
    name: str
    version: str
    form_schema: dict = Field(
        default_factory=dict,
        validation_alias="schema_json",
        serialization_alias="schema_json",
    )
