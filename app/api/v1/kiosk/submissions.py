from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.deps import KioskAuth
from app.db.session import get_db
from app.schemas.submission import GuestSubmissionCreate, GuestSubmissionResponse
from app.services.pdf import generate_guest_submission_pdf
from app.services.submissions import create_guest_submission

router = APIRouter(prefix="/submissions")


@router.post(
    "",
    response_model=GuestSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Utworzenie zgłoszenia gościa",
)
async def create_guest(
    data: GuestSubmissionCreate,
    _: KioskAuth,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GuestSubmissionResponse:
    submission = await create_guest_submission(db=db, data=data, settings=settings)
    return GuestSubmissionResponse.model_validate(submission)


@router.get(
    "/{submission_id}/pdf",
    summary="Generowanie PDF zgłoszenia gościa",
    responses={
        200: {"content": {"application/pdf": {}}},
    },
)
async def generate_guest_pdf(
    submission_id: UUID,
    _: KioskAuth,
    db: AsyncSession = Depends(get_db),
) -> Response:
    submission, pdf_bytes = await generate_guest_submission_pdf(db=db, submission_id=submission_id)
    filename = f"submission-{submission.start_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
