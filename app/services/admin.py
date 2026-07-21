from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
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


class AdminCannotDeleteSelf(AdminError):
    """Admin nie moze usunac wlasnego konta."""


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


async def get_admin_system_status(db: AsyncSession) -> dict:
    import asyncio

    settings = get_settings()
    checked_at = datetime.now(UTC)
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    from app.services.printer import get_printer_connection_status

    printer_status = await get_printer_connection_status(settings)

    return {
        "checked_at": checked_at,
        "api_ok": True,
        "db_ok": db_ok,
        "print_enabled": settings.print_enabled,
        "printer_status": printer_status,
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


async def get_admin_submission_png(
        db: AsyncSession,
        submission_id: UUID,
        page_index: int = 0,
        dpi: int = 150,
) -> tuple[bytes, str]:
    from app.services.pdf import generate_submission_png

    submission, png_bytes = await generate_submission_png(db, submission_id, page_index=page_index, dpi=dpi)
    file_id = submission.start_number if submission.start_number else submission.id
    filename = f"podglad_zgloszenia_{file_id}_page_{page_index}.png"
    return png_bytes, filename


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
        *,
        settings: Settings,
        force: bool = False,
) -> tuple[bytes, str, UUID, PrintJobStatus]:
    from app.services.pdf import generate_submission_pdf
    from app.services.printer import send_print_job

    print_job = await requeue_submission_for_print(db, submission_id)
    print_job_id = print_job.id
    submission, pdf_bytes = await generate_submission_pdf(db, submission_id)
    filename = _build_print_filename(submission)

    now = datetime.now(UTC)
    print_job.status = PrintJobStatus.PRINTING
    print_job.started_at = now
    current_attempts = print_job.__dict__.get("attempts")
    print_job.attempts = (current_attempts or 0) + 1
    await db.commit()

    try:
        await send_print_job(pdf_bytes=pdf_bytes, settings=settings, force=force)
    except Exception as e:
        print_job.status = PrintJobStatus.FAILED
        print_job.finished_at = datetime.now(UTC)
        print_job.last_error = str(e)
        submission.status = SubmissionStatus.PRINT_FAILED
        await db.commit()
        raise

    print_job.status = PrintJobStatus.DONE
    print_job.finished_at = datetime.now(UTC)
    print_job.last_error = None
    submission.status = SubmissionStatus.PRINT_DONE
    await db.commit()

    return pdf_bytes, filename, print_job_id, PrintJobStatus.DONE


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


async def delete_user_account(
        db: AsyncSession,
        user_id: UUID,
        admin_id: UUID,
) -> None:
    if user_id == admin_id:
        raise AdminCannotDeleteSelf("Nie mozesz usunac wlasnego konta")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AdminUserNotFound(f"Uzytkownik {user_id} nie zostal znaleziony")

    await db.delete(user)
    await db.commit()


async def get_admin_print_job_by_id(db: AsyncSession, job_id: UUID) -> PrintJob:
    result = await db.execute(select(PrintJob).where(PrintJob.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise AdminPrintJobNotFound(f"Zadanie druku {job_id} nie zostalo znalezione")
    return job

async def process_and_complete_print_job(
        db: AsyncSession,
        job_id: UUID,
        *,
        settings: Settings,
        force: bool = False,
) -> tuple[bytes, str, UUID, PrintJobStatus]:
    from app.services.pdf import generate_submission_pdf
    from app.services.printer import send_print_job

    job = await get_admin_print_job_by_id(db, job_id)
    existing_job_id = job.id
    submission, pdf_bytes = await generate_submission_pdf(db, job.submission_id)
    filename = _build_print_filename(submission)

    now = datetime.now(UTC)
    job.status = PrintJobStatus.PRINTING
    job.started_at = now
    current_attempts = job.__dict__.get("attempts")
    job.attempts = (current_attempts or 0) + 1

    try:
        await send_print_job(pdf_bytes=pdf_bytes, settings=settings, force=force)
    except Exception as e:
        job.status = PrintJobStatus.FAILED
        job.finished_at = datetime.now(UTC)
        job.last_error = str(e)
        submission.status = SubmissionStatus.PRINT_FAILED
        await db.commit()
        raise

    job.status = PrintJobStatus.DONE
    job.finished_at = datetime.now(UTC)
    job.last_error = None
    submission.status = SubmissionStatus.PRINT_DONE
    await db.commit()

    return pdf_bytes, filename, existing_job_id, PrintJobStatus.DONE