from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.db.session import get_db
from app.models.submission import Submission
from app.models.enums import SubmissionStatus
from app.models.print_job import PrintJob
from app.models.enums import PrintJobStatus

router = APIRouter(prefix="/admin/submissions", tags=["Admin Submissions"])


@router.get("")
async def get_submissions(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        status_filter: SubmissionStatus | None = Query(None, alias="status"),
        sequence_date: date | None = Query(None),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    """
    Pobiera listę zgłoszeń z możliwością filtrowania po statusie i dacie
    oraz obsługą paginacji. Dostępne tylko dla administratora.
    """
    query = select(Submission)

    if status_filter:
        query = query.where(Submission.status == status_filter)
    if sequence_date:
        query = query.where(Submission.sequence_date == sequence_date)

    query = query.order_by(Submission.created_at.desc())

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    submissions = result.scalars().all()

    count_query = select(func.count()).select_from(Submission)
    if status_filter:
        count_query = count_query.where(Submission.status == status_filter)
    if sequence_date:
        count_query = count_query.where(Submission.sequence_date == sequence_date)

    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    return {
        "items": submissions,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{submission_id}")
async def get_submission_details(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    """
    Pobiera pełne szczegóły wybranego zgłoszenia na podstawie ID.
    Dostępne tylko dla administratora.
    """
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zgłoszenie nie zostało znalezione"
        )

    return submission


@router.post("/{submission_id}/print")
async def queue_submission_for_print(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    """
    Ręcznie dodaje zgłoszenie do kolejki wydruku.
    """
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zgłoszenie nie zostało znalezione"
        )

    submission.status = SubmissionStatus.PRINT_QUEUED

    new_print_job = PrintJob(
        submission_id=submission.id,
        status=PrintJobStatus.QUEUED,
    )
    db.add(new_print_job)

    await db.commit()

    return {"message": "Zgłoszenie zostało pomyślnie dodane do kolejki wydruku."}