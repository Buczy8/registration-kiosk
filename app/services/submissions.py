from __future__ import annotations

from datetime import date, datetime
from typing import Awaitable, Callable
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.enums import SubmissionMode
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionCreate
from app.services.form_validation import get_missing_required_fields, validate_required_fields
from app.services.forms import get_active_form
from app.services.profiles import update_profile_from_submission
from app.services.signatures import parse_and_validate_signature, save_submission_signature
from app.services.submission_factory import build_submission


def get_sequence_date(settings: Settings) -> date:
    return datetime.now(ZoneInfo(settings.start_number_timezone)).date()


async def get_next_start_number(db: AsyncSession, sequence_date: date) -> int:
    result = await db.execute(
        text("SELECT next_start_number(:sequence_date)"),
        {"sequence_date": sequence_date},
    )
    return int(result.scalar_one())


async def create_guest_submission(
    db: AsyncSession,
    data: SubmissionCreate,
    settings: Settings,
) -> Submission:
    return await _create_submission_core(
        db=db,
        data=data,
        settings=settings,
        mode=SubmissionMode.GUEST,
        user_id=None,
    )


async def create_account_submission(
    db: AsyncSession,
    user: User,
    data: SubmissionCreate,
    settings: Settings,
) -> Submission:
    async def _update_profile() -> None:
        await update_profile_from_submission(
            db=db,
            user=user,
            payload=data.payload_json,
            vehicle_type=data.vehicle_type,
        )

    return await _create_submission_core(
        db=db,
        data=data,
        settings=settings,
        mode=SubmissionMode.ACCOUNT,
        user_id=user.id,
        post_flush_hook=_update_profile,
    )


async def _create_submission_core(
    *,
    db: AsyncSession,
    data: SubmissionCreate,
    settings: Settings,
    mode: SubmissionMode,
    user_id: UUID | None,
    post_flush_hook: Callable[[], Awaitable[None]] | None = None,
) -> Submission:
    form = await get_active_form(db)
    validate_required_fields(form.schema_json, data.payload_json)

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
    db.add(submission)

    try:
        await db.flush()
        signature_path, signature_hash, signed_at = save_submission_signature(
            settings, submission.id, image_bytes
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
    return submission
