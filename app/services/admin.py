from datetime import date, timedelta, UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PrintJobStatus, SubmissionStatus
from app.models.print_job import PrintJob
from app.models.submission import Submission
from app.models.user import User


async def get_admin_submissions(
        db: AsyncSession,
        status_filter: SubmissionStatus | None,
        sequence_date: date | None,
        limit: int,
        offset: int,
) -> tuple[list[Submission], int]:
    query = select(Submission)

    if status_filter:
        query = query.where(Submission.status == status_filter)
    if sequence_date:
        query = query.where(Submission.sequence_date == sequence_date)

    query = query.order_by(Submission.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    submissions = result.scalars().all()

    count_query = select(func.count()).select_from(Submission)
    if status_filter:
        count_query = count_query.where(Submission.status == status_filter)
    if sequence_date:
        count_query = count_query.where(Submission.sequence_date == sequence_date)

    total_count = (await db.execute(count_query)).scalar_one()

    return submissions, total_count


async def get_admin_submission_by_id(db: AsyncSession, submission_id: UUID) -> Submission:
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zgłoszenie nie zostało znalezione"
        )
    return submission


async def requeue_submission_for_print(db: AsyncSession, submission_id: UUID) -> None:
    submission = await get_admin_submission_by_id(db, submission_id)

    submission.status = SubmissionStatus.PRINT_QUEUED

    new_print_job = PrintJob(
        submission_id=submission.id,
        status=PrintJobStatus.QUEUED,
    )
    db.add(new_print_job)
    await db.commit()

async def get_admin_print_jobs(
        db: AsyncSession,
        status_filter: PrintJobStatus | None,
        limit: int,
        offset: int,
) -> tuple[list[PrintJob], int]:
    query = select(PrintJob).options(selectinload(PrintJob.submission))

    if status_filter:
        query = query.where(PrintJob.status == status_filter)

    query = query.order_by(PrintJob.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    print_jobs = result.scalars().all()

    count_query = select(func.count()).select_from(PrintJob)
    if status_filter:
        count_query = count_query.where(PrintJob.status == status_filter)

    total_count = (await db.execute(count_query)).scalar_one()

    return print_jobs, total_count

async def get_admin_users(
        db: AsyncSession,
        limit: int,
        offset: int,
) -> tuple[list[User], int]:
    query = select(User).options(selectinload(User.profile))
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    total_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    return users, total_count


async def lock_user_account(
        db: AsyncSession,
        user_id: UUID,
        admin_id: UUID,
        days: int
) -> None:
    if user_id == admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie możesz zablokować własnego konta"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie znaleziony"
        )

    user.locked_until = datetime.now(UTC) + timedelta(days=days)
    await db.commit()