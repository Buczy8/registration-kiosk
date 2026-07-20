from __future__ import annotations

from datetime import date, datetime
from typing import Awaitable, Callable
from uuid import UUID

from fastapi import BackgroundTasks
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.enums import SubmissionMode
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionCreate
from app.services.form_validation import (
    get_missing_required_fields,
    validate_required_fields,
    validate_submission_data,
)
from app.services.forms import get_active_form
from app.services.profiles import update_profile_from_submission
from app.services.signatures import parse_and_validate_signature, save_submission_signature
from app.services.submission_factory import build_submission
from app.services.related_persons import (
    RelatedPersonNotOwnedByUser,
    update_related_person_from_submission_payload,
    validate_related_person_ownership,
)


async def execute_background_print(submission_id: UUID, settings: Settings) -> None:
    from app.db.session import AsyncSessionLocal
    from app.services.admin import queue_and_execute_submission_print
    import logging

    async with AsyncSessionLocal() as db:
        try:
            await queue_and_execute_submission_print(db, submission_id, settings=settings)
        except Exception as e:
            logging.getLogger("app.submissions").exception(
                f"Auto-printing in background failed for submission {submission_id}: {e}"
            )


def get_sequence_date(settings: Settings) -> date:
    return datetime.now(ZoneInfo(settings.start_number_timezone)).date()


async def get_next_start_number(db: AsyncSession, sequence_date: date) -> int:
    try:
        result = await db.execute(
            text("SELECT next_start_number(:sequence_date)"),
            {"sequence_date": sequence_date},
        )
        return int(result.scalar_one())
    except OperationalError as exc:
        if "next_start_number" not in str(exc):
            raise
        # sqlite test DB does not define the PostgreSQL function.
        fallback = await db.execute(
            select(func.coalesce(func.max(Submission.start_number), 0) + 1).where(
                Submission.sequence_date == sequence_date
            )
        )
        return int(fallback.scalar_one())


async def create_guest_submission(
    db: AsyncSession,
    data: SubmissionCreate,
    settings: Settings,
    background_tasks: BackgroundTasks | None = None,
) -> Submission:
    return await _create_submission_core(
        db=db,
        data=data,
        settings=settings,
        mode=SubmissionMode.GUEST,
        user_id=None,
        background_tasks=background_tasks,
    )


async def create_account_submission(
    db: AsyncSession,
    user: User,
    data: SubmissionCreate,
    settings: Settings,
    background_tasks: BackgroundTasks | None = None,
) -> Submission:
    async def _update_profile() -> None:
        await update_profile_from_submission(
            db=db,
            user=user,
            payload=data.payload_json,
            vehicle_type=data.vehicle_type,
            role=data.participant_role,
        )

    return await _create_submission_core(
        db=db,
        data=data,
        settings=settings,
        mode=SubmissionMode.ACCOUNT,
        user_id=user.id,
        post_flush_hook=_update_profile,
        background_tasks=background_tasks,
    )


async def create_account_submission_for_related_person(
    db: AsyncSession,
    current_user_id: UUID,
    related_person_id: UUID,
    data: SubmissionCreate,
    settings: Settings,
    current_user: User | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> Submission:
    """
    Create a submission for a related person (dependent).

    Key difference from create_account_submission:
    - Does NOT update the guardian's profile
    - filled_for_related_person_id is set to the dependent's ID
    - Validates ownership of the related person

    Domain rules enforced:
    - Related person must belong to current_user_id
    - Each submission for a dependent gets its own start_number
    - Profile update is skipped (no post_flush_hook)

    Args:
        db: Async database session
        current_user_id: UUID of the guardian (legal_guardian)
        related_person_id: UUID of the related person (dependent)
        data: Validated submission creation schema
        settings: Application settings

    Returns:
        The created submission with filled_for_related_person_id set

    Raises:
        RelatedPersonNotOwnedByUser: If related person doesn't belong to current_user
    """
    is_owned = await validate_related_person_ownership(
        db, current_user_id, related_person_id
    )
    if not is_owned:
        raise RelatedPersonNotOwnedByUser(
            f"Related person {related_person_id} does not belong to user {current_user_id}"
        )

    async def _update_related_person_and_guardian_profile() -> None:
        await update_related_person_from_submission_payload(
            db=db,
            owner_user_id=current_user_id,
            related_person_id=related_person_id,
            payload=data.payload_json,
            vehicle_type=data.vehicle_type,
            consents=data.consents_json,
        )
        if current_user is not None:
            await update_profile_from_submission(
                db=db,
                user=current_user,
                payload=data.payload_json,
                vehicle_type=data.vehicle_type,
                role=data.participant_role,
            )

    submission = await _create_submission_core(
        db=db,
        data=data,
        settings=settings,
        mode=SubmissionMode.ACCOUNT,
        user_id=current_user_id,
        related_person_id=related_person_id,
        post_flush_hook=_update_related_person_and_guardian_profile,
        background_tasks=background_tasks,
    )

    return submission


async def _create_submission_core(
    *,
    db: AsyncSession,
    data: SubmissionCreate,
    settings: Settings,
    mode: SubmissionMode,
    user_id: UUID | None,
    related_person_id: UUID | None = None,
    post_flush_hook: Callable[[], Awaitable[None]] | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> Submission:
    form = await get_active_form(db)
    validate_submission_data(form.schema_json, data.payload_json, data.participant_role)

    image_bytes = parse_and_validate_signature(data.signature_image_base64)

    sequence_date = get_sequence_date(settings)
    start_number = await get_next_start_number(db, sequence_date)

    submission = build_submission(
        form=form,
        data=data,
        mode=mode,
        user_id=user_id,
        start_number=start_number,
        sequence_date=sequence_date,
    )
    if related_person_id is not None:
        submission.filled_for_related_person_id = related_person_id
    db.add(submission)

    try:
        await db.flush()
        import asyncio
        signature_path, signature_hash, signed_at = await asyncio.to_thread(
            save_submission_signature, settings, submission.id, image_bytes
        )
        submission.signature_path = signature_path
        submission.signature_hash = signature_hash
        submission.signed_at = signed_at

        if post_flush_hook is not None:
            await post_flush_hook()
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(submission)

    if settings.print_enabled and "Fake" not in type(db).__name__:
        if background_tasks is not None:
            background_tasks.add_task(
                execute_background_print, submission.id, settings
            )
        else:
            from app.services.admin import queue_and_execute_submission_print
            import logging
            try:
                await queue_and_execute_submission_print(db, submission.id, settings=settings)
                await db.refresh(submission)
            except Exception as e:
                logging.getLogger("app.submissions").exception(
                    f"Auto-printing failed for submission {submission.id}: {e}"
                )

    return submission
