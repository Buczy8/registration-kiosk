from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.related_person import (
    FormPreview,
    RelatedPersonCreate,
    RelatedPersonResponse,
    RelatedPersonWithPreview,
)
from app.schemas.submission import AccountSubmissionCreate, AccountSubmissionResponse
from app.services.related_persons import (
    create_related_person,
    get_form_preview_for_related_person,
    get_related_person,
    list_related_persons,
)
from app.services.submissions import create_account_submission_for_related_person

router = APIRouter(prefix="/account", tags=["account"])


@router.get(
    "/related-persons",
    response_model=list[RelatedPersonWithPreview],
    summary="Lista podopiecznych opiekuna",
)
async def list_related_persons_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[RelatedPersonWithPreview]:
    """
    GET /account/related-persons

    List all dependents (podopieczni) for the current guardian user.
    Includes preview of the last form submitted for each dependent.

    Returns:
        List of related persons with optional last_form_preview
    """
    return await list_related_persons(db, current_user.id)


@router.post(
    "/related-persons",
    response_model=RelatedPersonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dodaj nowego podopiecznego",
)
async def create_related_person_endpoint(
    data: RelatedPersonCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> RelatedPersonResponse:
    """
    POST /account/related-persons

    Create a new dependent (podopieczny) for the current guardian.

    Domain validation:
    - first_name, last_name: non-empty, max 100 chars
    - birth_date: optional, but if provided must not be in future

    Args:
        data: RelatedPersonCreate schema

    Returns:
        The newly created related person
    """
    person = await create_related_person(db, current_user.id, data)
    await db.commit()
    await db.refresh(person)

    return RelatedPersonResponse.model_validate(person)


@router.get(
    "/related-persons/{related_person_id}",
    response_model=RelatedPersonResponse,
    summary="Pobranie podopiecznego",
)
async def get_related_person_endpoint(
    related_person_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> RelatedPersonResponse:
    """
    GET /account/related-persons/{id}

    Get a specific dependent by ID.

    Raises:
        - 404: If dependent not found
        - 403: If dependent does not belong to current user
    """
    person = await get_related_person(db, current_user.id, related_person_id)
    return RelatedPersonResponse.model_validate(person)


@router.get(
    "/related-persons/{related_person_id}/form-preview",
    response_model=FormPreview | None,
    summary="Podgląd ostatniego formularza podopiecznego",
)
async def get_form_preview_endpoint(
    related_person_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> FormPreview | None:
    """
    GET /account/related-persons/{id}/form-preview

    Get preview of the last form submitted for a dependent.

    Returns:
        FormPreview snapshot of the last submission, or None if no submissions exist
    """
    await get_related_person(db, current_user.id, related_person_id)

    preview = await get_form_preview_for_related_person(db, related_person_id)
    return preview


@router.post(
    "/submissions/for-related-person",
    response_model=AccountSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submission za podopiecznego",
)
async def create_submission_for_related_person_endpoint(
    data: AccountSubmissionCreate,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    related_person_id: UUID = Query(
        ..., description="UUID of the related person (dependent)"
    ),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AccountSubmissionResponse:
    """
    POST /account/submissions/for-related-person?related_person_id={id}

    Create a submission for a dependent (podopieczny).

    Key differences from regular account submission:
    - Does NOT update guardian's profile
    - Each submission gets its own start_number
    - filled_for_related_person_id is set to the dependent

    Args:
        data: AccountSubmissionCreate schema
        related_person_id: UUID of the dependent (query param)

    Returns:
        The created submission

    Raises:
        - 400: If validation fails
        - 403: If dependent does not belong to current user
        - 404: If dependent not found
    """
    submission = await create_account_submission_for_related_person(
        db=db,
        current_user_id=current_user.id,
        related_person_id=related_person_id,
        data=data,
        settings=settings,
        current_user=current_user,
        background_tasks=background_tasks,
    )

    return AccountSubmissionResponse.model_validate(submission)
