from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ParticipantRole, VehicleType
from app.models.user import User, UserProfile
from app.schemas.profile import FormPrefillResponse, ProfileResponse, VehicleData


async def get_or_create_profile(db: AsyncSession, user_id: UUID) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is not None:
        return profile

    profile = UserProfile(user_id=user_id, vehicles_json={})
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


def build_vehicle_from_json(
    vehicles_json: dict[str, Any] | None, vehicle_type: VehicleType
) -> VehicleData | None:
    if not isinstance(vehicles_json, dict):
        return None

    raw_vehicle = vehicles_json.get(vehicle_type.value)
    if not isinstance(raw_vehicle, dict):
        return None

    brand_model = raw_vehicle.get("brand_model")
    registration_number = raw_vehicle.get("registration_number")
    if not brand_model or not registration_number:
        return None

    return VehicleData(
        brand_model=str(brand_model),
        registration_number=str(registration_number),
    )


def _parse_last_participant_role(value: str | None) -> ParticipantRole | None:
    if not value:
        return None
    try:
        return ParticipantRole(value)
    except ValueError:
        return None


def _parse_last_vehicle_type(value: str | None) -> VehicleType | None:
    if not value:
        return None
    try:
        return VehicleType(value)
    except ValueError:
        return None


async def get_form_prefill(
    db: AsyncSession,
    user: User,
    role: ParticipantRole,
    vehicle_type: VehicleType,
) -> FormPrefillResponse:
    profile = await get_or_create_profile(db, user.id)
    vehicle = build_vehicle_from_json(profile.vehicles_json, vehicle_type)

    return FormPrefillResponse(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        address=profile.address,
        birth_date=profile.birth_date,
        document_number=profile.document_number,
        pesel=profile.pesel,
        id_card_series=profile.id_card_series,
        id_card_number=profile.id_card_number,
        ice_name=profile.ice_name,
        ice_phone=profile.ice_phone,
        participant_role=role,
        vehicle_type=vehicle_type,
        vehicle=vehicle,
    )


async def get_profile_response(db: AsyncSession, user: User) -> ProfileResponse:
    profile = await get_or_create_profile(db, user.id)
    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        is_superuser=bool(user.is_superuser),
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        address=profile.address,
        birth_date=profile.birth_date,
        document_number=profile.document_number,
        pesel=profile.pesel,
        id_card_series=profile.id_card_series,
        id_card_number=profile.id_card_number,
        ice_name=profile.ice_name,
        ice_phone=profile.ice_phone,
        last_participant_role=_parse_last_participant_role(profile.last_participant_role),
        last_vehicle_type=_parse_last_vehicle_type(profile.last_vehicle_type),
        vehicles_json=profile.vehicles_json,
    )


def extract_profile_fields_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_name": payload.get("first_name"),
        "last_name": payload.get("last_name"),
        "phone": payload.get("phone"),
        "address": payload.get("residence_address") or payload.get("address"),
        "birth_date": payload.get("birth_date"),
        "document_number": payload.get("document_number"),
        "pesel": payload.get("pesel"),
        "id_card_series": payload.get("id_card_series"),
        "id_card_number": payload.get("id_card_number"),
        "ice_name": payload.get("ice_name") or payload.get("emergency_contact_name"),
        "ice_phone": payload.get("ice_phone") or payload.get("emergency_contact_phone"),
    }


async def update_profile_from_submission(
    db: AsyncSession,
    user: User,
    payload: dict[str, Any],
    vehicle_type: VehicleType,
    role: ParticipantRole,
) -> None:
    profile = await get_or_create_profile(db, user.id)
    fields = extract_profile_fields_from_payload(payload)

    for key in ("first_name", "last_name", "phone"):
        value = fields.get(key)
        if value not in (None, ""):
            setattr(user, key, value)

    for key in (
        "address",
        "birth_date",
        "document_number",
        "pesel",
        "id_card_series",
        "id_card_number",
        "ice_name",
        "ice_phone",
    ):
        value = fields.get(key)
        if value not in (None, ""):
            setattr(profile, key, value)

    profile.last_participant_role = role.value
    profile.last_vehicle_type = vehicle_type.value

    brand_model = payload.get("vehicle_brand_model")
    if not brand_model:
        brand = payload.get("vehicle_brand")
        model = payload.get("vehicle_model")
        if brand or model:
            brand_model = f"{(brand or '').strip()} {(model or '').strip()}".strip()
    registration_number = payload.get("vehicle_registration_number")

    merged_vehicles = dict(profile.vehicles_json or {})
    if brand_model and registration_number:
        merged_vehicles[vehicle_type.value] = {
            "brand_model": str(brand_model),
            "registration_number": str(registration_number),
        }
    profile.vehicles_json = merged_vehicles
