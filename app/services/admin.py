from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    ParticipantRole,
    PrintJobStatus,
    SubmissionMode,
    SubmissionStatus,
    VehicleType,
)
from app.models.print_job import PrintJob
from app.models.submission import Submission
from app.models.user import User


class AdminError(Exception):
    """Bazowy wyjatek domenowy panelu admina."""


class AdminSubmissionNotFound(AdminError):
    """Zgloszenie nie zostalo znalezione."""


class AdminUserNotFound(AdminError):
    """Uzytkownik nie zostal znaleziony."""


class AdminCannotLockSelf(AdminError):
    """Admin nie moze zablokowac wlasnego konta."""


class AdminPrintJobNotFound(AdminError):
    """Zadanie wydruku nie zostalo znalezione."""


def _attach_submission_list_metadata(submission: Submission) -> None:
    try:
        payload = submission.payload_json or {}
        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        submission.display_name = full_name or None
    except Exception:
        submission.display_name = None

    try:
        print_jobs = list(submission.print_jobs or [])
    except Exception:
        print_jobs = []
    if print_jobs:
        latest_job = max(print_jobs, key=lambda job: job.queued_at)
        submission.last_print_job_id = latest_job.id
        submission.last_print_status = latest_job.status
        submission.last_print_at = latest_job.queued_at
    else:
        submission.last_print_job_id = None
        submission.last_print_status = None
        submission.last_print_at = None


async def get_admin_dashboard_stats(db: AsyncSession, sequence_date: date) -> dict:
    day_filter = Submission.sequence_date == sequence_date

    total_submissions = (
        await db.execute(select(func.count()).select_from(Submission).where(day_filter))
    ).scalar_one()

    status_rows = (
        await db.execute(
            select(Submission.status, func.count())
            .where(day_filter)
            .group_by(Submission.status)
        )
    ).all()
    status_counts = {status: count for status, count in status_rows}

    mode_rows = (
        await db.execute(
            select(Submission.mode, func.count())
            .where(day_filter)
            .group_by(Submission.mode)
        )
    ).all()
    mode_counts = {mode: count for mode, count in mode_rows}

    last_start_number = (
        await db.execute(
            select(func.max(Submission.start_number)).where(day_filter)
        )
    ).scalar_one()

    return {
        "sequence_date": sequence_date,
        "total_submissions": total_submissions,
        "submitted_count": status_counts.get(SubmissionStatus.SUBMITTED, 0),
        "print_queued_count": status_counts.get(SubmissionStatus.PRINT_QUEUED, 0),
        "print_done_count": status_counts.get(SubmissionStatus.PRINT_DONE, 0),
        "print_failed_count": status_counts.get(SubmissionStatus.PRINT_FAILED, 0),
        "guest_count": mode_counts.get(SubmissionMode.GUEST, 0),
        "account_count": mode_counts.get(SubmissionMode.ACCOUNT, 0),
        "last_start_number": last_start_number,
    }


async def get_admin_submissions(
        db: AsyncSession,
        status_filter: SubmissionStatus | None,
        sequence_date: date | None,
        mode_filter: SubmissionMode | None,
        role_filter: ParticipantRole | None,
        vehicle_type_filter: VehicleType | None,
        last_name_query: str | None,
        limit: int,
        offset: int,
) -> tuple[list[Submission], int]:
    query = select(Submission).options(selectinload(Submission.print_jobs))

    if status_filter:
        query = query.where(Submission.status == status_filter)
    if sequence_date:
        query = query.where(Submission.sequence_date == sequence_date)
    if mode_filter:
        query = query.where(Submission.mode == mode_filter)
    if role_filter:
        query = query.where(Submission.participant_role == role_filter)
    if vehicle_type_filter:
        query = query.where(Submission.vehicle_type == vehicle_type_filter)
    if last_name_query:
        query = query.where(
            Submission.payload_json["last_name"].astext.ilike(f"%{last_name_query.strip()}%")
        )

    query = query.order_by(Submission.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    submissions = result.scalars().all()

    for submission in submissions:
        _attach_submission_list_metadata(submission)

    count_query = select(func.count()).select_from(Submission)
    if status_filter:
        count_query = count_query.where(Submission.status == status_filter)
    if sequence_date:
        count_query = count_query.where(Submission.sequence_date == sequence_date)
    if mode_filter:
        count_query = count_query.where(Submission.mode == mode_filter)
    if role_filter:
        count_query = count_query.where(Submission.participant_role == role_filter)
    if vehicle_type_filter:
        count_query = count_query.where(Submission.vehicle_type == vehicle_type_filter)
    if last_name_query:
        count_query = count_query.where(
            Submission.payload_json["last_name"].astext.ilike(f"%{last_name_query.strip()}%")
        )

    total_count = (await db.execute(count_query)).scalar_one()

    return submissions, total_count


async def get_admin_submission_by_id(db: AsyncSession, submission_id: UUID) -> Submission:
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()

    if submission is None:
        raise AdminSubmissionNotFound(f"Zgloszenie {submission_id} nie zostalo znalezione")
    return submission


async def get_admin_submission_pdf(
        db: AsyncSession,
        submission_id: UUID,
) -> tuple[bytes, str]:
    from app.services.pdf import generate_submission_pdf

    submission, pdf_bytes = await generate_submission_pdf(db, submission_id)
    return pdf_bytes, _build_print_filename(submission)


def _build_print_filename(submission: Submission) -> str:
    file_id = submission.start_number if submission.start_number else submission.id
    return f"wydruk_zgloszenia_{file_id}.pdf"


async def requeue_submission_for_print(db: AsyncSession, submission_id: UUID) -> PrintJob:
    submission = await get_admin_submission_by_id(db, submission_id)

    submission.status = SubmissionStatus.PRINT_QUEUED

    new_print_job = PrintJob(
        submission_id=submission.id,
        status=PrintJobStatus.QUEUED,
    )
    db.add(new_print_job)
    await db.flush()
    return new_print_job


async def queue_and_execute_submission_print(
        db: AsyncSession,
        submission_id: UUID,
) -> tuple[bytes, str]:
    from app.services.pdf import generate_submission_pdf

    print_job = await requeue_submission_for_print(db, submission_id)
    submission, pdf_bytes = await generate_submission_pdf(db, submission_id)
    filename = _build_print_filename(submission)

    print_job.status = PrintJobStatus.DONE
    submission.status = SubmissionStatus.PRINT_DONE
    await db.commit()

    return pdf_bytes, filename


async def get_admin_print_jobs(
        db: AsyncSession,
        status_filter: PrintJobStatus | None,
        sequence_date: date | None,
        limit: int,
        offset: int,
) -> tuple[list[PrintJob], int]:
    query = select(PrintJob).options(selectinload(PrintJob.submission))

    if sequence_date:
        query = query.join(Submission, PrintJob.submission_id == Submission.id).where(
            Submission.sequence_date == sequence_date
        )

    if status_filter:
        query = query.where(PrintJob.status == status_filter)

    query = query.order_by(PrintJob.queued_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    print_jobs = result.scalars().all()

    count_query = select(func.count()).select_from(PrintJob)
    if sequence_date:
        count_query = count_query.join(
            Submission, PrintJob.submission_id == Submission.id
        ).where(Submission.sequence_date == sequence_date)
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
        raise AdminCannotLockSelf("Nie mozesz zablokowac wlasnego konta")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AdminUserNotFound(f"Uzytkownik {user_id} nie zostal znaleziony")

    user.locked_until = datetime.now(UTC) + timedelta(days=days)
    await db.commit()


async def unlock_user_account(db: AsyncSession, user_id: UUID) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AdminUserNotFound(f"Uzytkownik {user_id} nie zostal znaleziony")

    user.locked_until = None
    user.failed_login_count = 0
    await db.commit()


async def get_admin_print_job_by_id(db: AsyncSession, job_id: UUID) -> PrintJob:
    result = await db.execute(select(PrintJob).where(PrintJob.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise AdminPrintJobNotFound(f"Zadanie druku {job_id} nie zostalo znalezione")
    return job

async def process_and_complete_print_job(db: AsyncSession, job_id: UUID) -> tuple[bytes, str]:
    from app.services.pdf import generate_submission_pdf

    job = await get_admin_print_job_by_id(db, job_id)
    submission, pdf_bytes = await generate_submission_pdf(db, job.submission_id)
    filename = _build_print_filename(submission)

    job.status = PrintJobStatus.DONE
    submission.status = SubmissionStatus.PRINT_DONE
    await db.commit()

    return pdf_bytes, filename