from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import KioskAuth, OptionalCurrentUser
from app.db.session import get_db
from app.schemas.submission import (
    AccountSubmissionCreate,
    AccountSubmissionResponse,
    GuestSubmissionCreate,
    GuestSubmissionResponse,
)
from app.services.pdf import generate_guest_submission_pdf
from app.services.submissions import create_account_submission, create_guest_submission

router = APIRouter(prefix="/submissions")


def _validation_error_response(exc: ValidationError) -> Response:
    from fastapi.exceptions import RequestValidationError

    raise RequestValidationError(exc.errors())


@router.post(
    "",
    response_model=GuestSubmissionResponse | AccountSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Utworzenie zgłoszenia (guest lub account)",
    description=(
        "Tworzy zgłoszenie w trybie guest lub account.\n\n"
        "Autoryzacja dwutorowa:\n"
        "- Kiosk token (nagłówek X-Kiosk-Token) jest wymagany zawsze.\n"
        "- Jeśli dodatkowo przesłany zostanie prawidłowy Bearer JWT, zgłoszenie "
        "tworzone jest w trybie account (mode=account, user_id ustawiony, profil "
        "aktualizowany po zapisie za siebie).\n"
        "- Bez Bearer JWT zgłoszenie tworzone jest jako guest (mode=guest)."
    ),
)
async def create_submission(
    _: KioskAuth,
    user: OptionalCurrentUser,
    body: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GuestSubmissionResponse | AccountSubmissionResponse:
    if user is not None:
        try:
            account_data = AccountSubmissionCreate.model_validate(body)
        except ValidationError as exc:
            _validation_error_response(exc)
        submission = await create_account_submission(
            db=db, user=user, data=account_data, settings=settings
        )
        return AccountSubmissionResponse.model_validate(submission)

    try:
        guest_data = GuestSubmissionCreate.model_validate(body)
    except ValidationError as exc:
        _validation_error_response(exc)
    submission = await create_guest_submission(db=db, data=guest_data, settings=settings)
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
