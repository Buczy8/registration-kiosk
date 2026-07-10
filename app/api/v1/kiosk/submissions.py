from uuid import UUID

from fastapi import APIRouter, Depends, Response, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import KioskAuth, OptionalCurrentUser
from app.db.session import get_db
from app.schemas.submission import (
    AccountSubmissionResponse,
    GuestSubmissionResponse,
    SubmissionCreate,
)
from app.services.pdf import generate_submission_pdf
from app.services.submissions import create_account_submission, create_guest_submission

router = APIRouter(prefix="/submissions")


@router.post(
    "",
    response_model=GuestSubmissionResponse | AccountSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Utworzenie zgłoszenia (guest lub account)",
    description=(
        "Tworzy zgłoszenie w trybie guest lub account.\n\n"
        "Autoryzacja dwutorowa:\n"
        "- Kiosk token (nagłówek X-Kiosk-Token) jest wymagany zawsze.\n"
        "- Jeśli dodatkowo zalogowany jest użytkownik (przez nagłówek Bearer JWT lub ciasteczko kiosk_access_token), "
        "zgłoszenie tworzone jest w trybie account (mode=account, user_id ustawiony, profil "
        "aktualizowany po zapisie za siebie)."
    ),
)
async def create_submission(
    _: KioskAuth,
    user: OptionalCurrentUser,
    body: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GuestSubmissionResponse | AccountSubmissionResponse:
    if user is not None:
        submission = await create_account_submission(
            db=db, user=user, data=body, settings=settings, background_tasks=background_tasks
        )
        return AccountSubmissionResponse.model_validate(submission)

    submission = await create_guest_submission(
        db=db, data=body, settings=settings, background_tasks=background_tasks
    )
    return GuestSubmissionResponse.model_validate(submission)


@router.get(
    "/{submission_id}/pdf",
    summary="Generowanie PDF zgłoszenia",
    responses={
        200: {"content": {"application/pdf": {}}},
    },
)
async def generate_submission_pdf_endpoint(
    submission_id: UUID,
    _: KioskAuth,
    db: AsyncSession = Depends(get_db),
) -> Response:
    submission, pdf_bytes = await generate_submission_pdf(db=db, submission_id=submission_id)
    filename = f"submission-{submission.start_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
