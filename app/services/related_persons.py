"""
Service layer for related persons (dependents).

Domain: RelatedPerson aggregate
- Manages dependents belonging to a guardian (legal_guardian role)
- Enforces ownership constraints
- Provides form preview (last submission for dependent)
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enums import ParticipantRole, SubmissionMode
from app.models.related_person import RelatedPerson
from app.models.submission import Submission
from app.schemas.related_person import (
    FormPreview,
    RelatedPersonCreate,
    RelatedPersonResponse,
    RelatedPersonWithPreview,
)


class RelatedPersonError(Exception):
    """Base domain exception for related persons"""


class RelatedPersonNotFound(RelatedPersonError):
    """Related person does not exist"""


class InvalidPersonName(RelatedPersonError):
    """Person name validation failed"""


class RelatedPersonNotOwnedByUser(RelatedPersonError):
    """Related person does not belong to the specified user"""


async def list_related_persons(
    db: AsyncSession,
    owner_user_id: UUID,
) -> list[RelatedPersonWithPreview]:
    """
    List all related persons for a guardian user with their last form preview.

    Args:
        db: Async database session
        owner_user_id: UUID of the guardian (legal_guardian user)

    Returns:
        List of related persons with optional last form preview
    """
    stmt = (
        select(RelatedPerson)
        .where(RelatedPerson.owner_user_id == owner_user_id)
        .order_by(
            RelatedPerson.created_at.desc(),
            RelatedPerson.first_name.asc(),
            RelatedPerson.last_name.asc(),
        )
    )

    result = await db.execute(stmt)
    related_persons = result.scalars().all()

    response_list = []
    for person in related_persons:
        preview = await _get_form_preview_for_related_person(db, person.id)
        response_list.append(
            RelatedPersonWithPreview(
                id=person.id,
                first_name=person.first_name,
                last_name=person.last_name,
                birth_date=person.birth_date,
                guardian_relation=person.guardian_relation,
                image_publication_consent=person.image_publication_consent,
                vehicle_type=person.vehicle_type,
                vehicle_brand=person.vehicle_brand,
                vehicle_model=person.vehicle_model,
                vehicle_registration_number=person.vehicle_registration_number,
                created_at=person.created_at,
                updated_at=person.updated_at,
                last_form_preview=preview,
            )
        )

    return response_list


async def get_related_person(
    db: AsyncSession,
    owner_user_id: UUID,
    related_person_id: UUID,
) -> RelatedPerson:
    """
    Get a related person by ID with ownership validation.

    Args:
        db: Async database session
        owner_user_id: UUID of the guardian
        related_person_id: UUID of the related person

    Returns:
        The related person model

    Raises:
        RelatedPersonNotFound: If related person does not exist
        RelatedPersonNotOwnedByUser: If ownership check fails
    """
    stmt = select(RelatedPerson).where(RelatedPerson.id == related_person_id)
    result = await db.execute(stmt)
    person = result.scalars().first()

    if person is None:
        raise RelatedPersonNotFound(f"Related person {related_person_id} not found")

    if person.owner_user_id != owner_user_id:
        raise RelatedPersonNotOwnedByUser(
            f"Related person {related_person_id} does not belong to user {owner_user_id}"
        )

    return person


async def create_related_person(
    db: AsyncSession,
    owner_user_id: UUID,
    data: RelatedPersonCreate,
) -> RelatedPerson:
    """
    Create a new related person (dependent) for a guardian.

    Domain invariants enforced:
    - first_name, last_name: non-empty, max 100 chars
    - birth_date: if provided, not in future
    - owner_user_id must be valid (FK constraint in DB)

    Args:
        db: Async database session
        owner_user_id: UUID of the guardian (legal_guardian)
        data: Validated creation schema

    Returns:
        The newly created related person

    Raises:
        InvalidPersonName: If validation fails (should not happen with Pydantic)
        RelatedError: For other domain violations
    """
    person = RelatedPerson(
        owner_user_id=owner_user_id,
        first_name=data.first_name,
        last_name=data.last_name,
        birth_date=data.birth_date,
        guardian_relation=data.guardian_relation,
        image_publication_consent=data.image_publication_consent,
        vehicle_type=data.vehicle_type,
        vehicle_brand=data.vehicle_brand,
        vehicle_model=data.vehicle_model,
        vehicle_registration_number=data.vehicle_registration_number,
    )

    db.add(person)
    await db.flush()

    return person


def _normalized_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


async def update_related_person_from_submission_payload(
    db: AsyncSession,
    owner_user_id: UUID,
    related_person_id: UUID,
    *,
    payload: dict,
    vehicle_type: object,
    consents: dict,
) -> RelatedPerson:
    """Persist edits made in the guardian form back to the dependent record."""
    person = await get_related_person(db, owner_user_id, related_person_id)

    first_name = _normalized_optional_text(
        payload.get("minor_first_name") or payload.get("first_name")
    )
    last_name = _normalized_optional_text(
        payload.get("minor_last_name") or payload.get("last_name")
    )
    guardian_relation = _normalized_optional_text(payload.get("guardian_relation"))

    if first_name is not None:
        person.first_name = first_name
    if last_name is not None:
        person.last_name = last_name
    if guardian_relation is not None:
        person.guardian_relation = guardian_relation

    person.image_publication_consent = bool(
        consents.get("image_publication", person.image_publication_consent)
    )
    person.vehicle_type = vehicle_type

    for field_name in (
        "vehicle_brand",
        "vehicle_model",
        "vehicle_registration_number",
    ):
        if field_name in payload:
            setattr(person, field_name, _normalized_optional_text(payload.get(field_name)))

    return person


async def get_form_preview_for_related_person(
    db: AsyncSession,
    related_person_id: UUID,
) -> FormPreview | None:
    """
    Get the preview of the last form submitted for a related person.

    Query: submissions WHERE filled_for_related_person_id = {id}
           ORDER BY created_at DESC LIMIT 1

    Args:
        db: Async database session
        related_person_id: UUID of the related person

    Returns:
        FormPreview snapshot of the last submission, or None if no submissions exist
    """
    return await _get_form_preview_for_related_person(db, related_person_id)


async def _get_form_preview_for_related_person(
    db: AsyncSession,
    related_person_id: UUID,
) -> FormPreview | None:
    """Internal helper to fetch form preview for a related person."""
    stmt = (
        select(Submission)
        .where(
            (Submission.filled_for_related_person_id == related_person_id)
            & (Submission.mode == SubmissionMode.ACCOUNT)
        )
        .order_by(
            Submission.created_at.desc(),
            Submission.signed_at.desc(),
            Submission.start_number.desc(),
            Submission.id.desc(),
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    submission = result.scalars().first()

    if submission is None:
        return None

    return FormPreview(
        submission_id=submission.id,
        start_number=submission.start_number,
        participant_role=submission.participant_role,
        vehicle_type=submission.vehicle_type,
        signed_at=submission.signed_at,
    )


async def validate_related_person_ownership(
    db: AsyncSession,
    owner_user_id: UUID,
    related_person_id: UUID,
) -> bool:
    """
    Check if a related person belongs to the specified user (pure function).

    Args:
        db: Async database session
        owner_user_id: UUID of the guardian
        related_person_id: UUID of the related person

    Returns:
        True if ownership is valid, False otherwise
    """
    stmt = (
        select(RelatedPerson.id)
        .where(
            (RelatedPerson.id == related_person_id)
            & (RelatedPerson.owner_user_id == owner_user_id)
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
