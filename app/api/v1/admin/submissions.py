from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.db.session import get_db
from app.models.enums import SubmissionStatus
from app.schemas.admin import (
    AdminSubmissionDetail,
    AdminSubmissionListResponse,
)
from app.schemas.auth import MessageResponse
from app.services import admin as admin_services

router = APIRouter(prefix="/admin/submissions", tags=["Admin Submissions"])


@router.get("", response_model=AdminSubmissionListResponse)
async def get_submissions(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        status_filter: SubmissionStatus | None = Query(None, alias="status"),
        sequence_date: date | None = Query(None),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    submissions, total_count = await admin_services.get_admin_submissions(
        db, status_filter, sequence_date, limit, offset
    )

    return {
        "items": submissions,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{submission_id}", response_model=AdminSubmissionDetail)
async def get_submission_details(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    return await admin_services.get_admin_submission_by_id(db, submission_id)


@router.post("/{submission_id}/print", response_model=MessageResponse)
async def queue_submission_for_print(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    await admin_services.requeue_submission_for_print(db, submission_id)
    return {"message": "Zgłoszenie zostało pomyślnie dodane do kolejki wydruku."}
