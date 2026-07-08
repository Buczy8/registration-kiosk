# app/api/v1/admin/print_jobs.py
from fastapi import APIRouter, Depends, Query
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
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    print_jobs, total_count = await admin_services.get_admin_print_jobs(
        db, status_filter, limit, offset
    )

    return {
        "items": print_jobs,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }
