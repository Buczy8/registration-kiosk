from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.deps import KioskAuth
from app.db.session import get_db
from app.schemas.form import ActiveFormResponse
from app.services.forms import get_active_form

router = APIRouter(prefix="/forms")


@router.get(
    "/active",
    response_model=ActiveFormResponse,
    summary="Aktywny formularz kiosku",
)
async def active_form(_: KioskAuth, db: AsyncSession = Depends(get_db)) -> ActiveFormResponse:
    form = await get_active_form(db)
    return ActiveFormResponse.model_validate(form)
