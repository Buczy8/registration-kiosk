from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.db.session import get_db
from app.models.print_job import PrintJob
from app.models.enums import PrintJobStatus

router = APIRouter(prefix="/admin/print-jobs", tags=["Admin Print Jobs"])


@router.get("")
async def get_print_jobs(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        status_filter: PrintJobStatus | None = Query(None, alias="status"),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    """
    Pobiera listę zadań drukowania. Dostępne tylko dla administratora.
    """
    query = select(PrintJob).options(selectinload(PrintJob.submission))

    if status_filter:
        query = query.where(PrintJob.status == status_filter)

    query = query.order_by(PrintJob.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    print_jobs = result.scalars().all()

    count_query = select(func.count()).select_from(PrintJob)
    if status_filter:
        count_query = count_query.where(PrintJob.status == status_filter)

    total_count = (await db.execute(count_query)).scalar_one()

    return {
        "items": print_jobs,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }