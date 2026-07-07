from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import KioskAndUser, verify_kiosk_and_user
from app.db.session import get_db
from app.models.enums import ParticipantRole, VehicleType
from app.schemas.profile import FormPrefillResponse, ProfileResponse
from app.services.profiles import get_form_prefill, get_profile_response

router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Pobranie profilu aktualnie zalogowanego uzytkownika",
)
async def get_my_profile(
    auth: KioskAndUser = Depends(verify_kiosk_and_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    return await get_profile_response(db=db, user=auth.user)


@router.get(
    "/form-prefill",
    response_model=FormPrefillResponse,
    summary="Prefill danych formularza dla aktualnego uzytkownika",
)
async def get_my_form_prefill(
    role: ParticipantRole,
    vehicle_type: VehicleType,
    auth: KioskAndUser = Depends(verify_kiosk_and_user),
    db: AsyncSession = Depends(get_db),
) -> FormPrefillResponse:
    return await get_form_prefill(
        db=db,
        user=auth.user,
        role=role,
        vehicle_type=vehicle_type,
    )
