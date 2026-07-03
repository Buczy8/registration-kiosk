from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.deps import KioskAuth
from app.db.session import get_db
from app.schemas.submission import GuestSubmissionCreate, GuestSubmissionResponse
from app.services.submissions import create_guest_submission

router = APIRouter(prefix="/submissions")


@router.post(
    "",
    response_model=GuestSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Utworzenie zgłoszenia gościa",
)
def create_guest(
    data: GuestSubmissionCreate,
    _: KioskAuth,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GuestSubmissionResponse:
    submission = create_guest_submission(db=db, data=data, settings=settings)
    return GuestSubmissionResponse.model_validate(submission)
