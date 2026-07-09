from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.db.session import get_db
from app.models.enums import PrintJobStatus
from app.schemas.admin import AdminPrintJobListResponse
from app.services import admin as admin_services

router = APIRouter(prefix="/admin/print-jobs", tags=["Admin Print Jobs"])


@router.get("", response_model=AdminPrintJobListResponse)
async def get_print_jobs(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        status_filter: PrintJobStatus | None = Query(None, alias="status"),
        sequence_date: date | None = Query(None),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    print_jobs, total_count = await admin_services.get_admin_print_jobs(
        db, status_filter, sequence_date, limit, offset
    )

    return {
        "items": print_jobs,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{job_id}/print")
async def execute_print_job(
        job_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    try:
        pdf_bytes, filename = await admin_services.process_and_complete_print_job(db, job_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except admin_services.AdminPrintJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))