from fastapi import APIRouter, Depends
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
def active_form(_: KioskAuth, db: Session = Depends(get_db)) -> ActiveFormResponse:
    return ActiveFormResponse.model_validate(get_active_form(db))
