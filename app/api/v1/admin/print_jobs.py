from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.enums import PrintJobStatus
from app.schemas.admin import AdminPrintActionResponse, AdminPrintJobListResponse
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


@router.post("/{job_id}/print", response_model=AdminPrintActionResponse)
async def execute_print_job(
        job_id: UUID,
        admin: CurrentAdminUser,
        settings: Settings = Depends(get_settings),
        db: AsyncSession = Depends(get_db),
):
    try:
        _, _, job_id_result, job_status = await admin_services.process_and_complete_print_job(
            db, job_id, settings=settings, force=True
        )
        return AdminPrintActionResponse(
            message="Print job completed",
            job_id=job_id_result,
            status=job_status,
        )
    except admin_services.AdminPrintJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))