from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.enums import ParticipantRole, SubmissionMode, SubmissionStatus, VehicleType
from app.schemas.admin import (
    AdminPrintActionResponse,
    AdminSubmissionDetail,
    AdminSubmissionListResponse,
)
from app.services import admin as admin_services

router = APIRouter(prefix="/admin/submissions", tags=["Admin Submissions"])


@router.get("", response_model=AdminSubmissionListResponse)
async def get_submissions(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        status_filter: SubmissionStatus | None = Query(None, alias="status"),
        sequence_date: date | None = Query(None),
        mode_filter: SubmissionMode | None = Query(None, alias="mode"),
        role_filter: ParticipantRole | None = Query(None, alias="role"),
        vehicle_type_filter: VehicleType | None = Query(None, alias="vehicle_type"),
        last_name: str | None = Query(None, min_length=1, max_length=120),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    submissions, total_count = await admin_services.get_admin_submissions(
        db,
        status_filter,
        sequence_date,
        mode_filter,
        role_filter,
        vehicle_type_filter,
        last_name,
        limit,
        offset,
    )

    return {
        "items": submissions,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{submission_id}/pdf")
async def get_submission_pdf(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    pdf_bytes, filename = await admin_services.get_admin_submission_pdf(db, submission_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{submission_id}/png")
async def get_submission_png(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        page: int = Query(0, ge=0, description="Numer strony PDF (indeksowany od 0)"),
        dpi: int = Query(150, ge=72, le=600, description="Rozdzielczość renderingu DPI"),
):
    png_bytes, filename = await admin_services.get_admin_submission_png(db, submission_id, page_index=page, dpi=dpi)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )



@router.get("/{submission_id}", response_model=AdminSubmissionDetail)
async def get_submission_details(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    return await admin_services.get_admin_submission_by_id(db, submission_id)


@router.post("/{submission_id}/print", response_model=AdminPrintActionResponse)
async def queue_submission_for_print(
        submission_id: UUID,
        admin: CurrentAdminUser,
        settings: Settings = Depends(get_settings),
        db: AsyncSession = Depends(get_db),
):
    _, _, job_id, job_status = await admin_services.queue_and_execute_submission_print(
        db, submission_id, settings=settings, force=True
    )
    return AdminPrintActionResponse(
        message="Print job completed",
        job_id=job_id,
        status=job_status,
    )


@router.delete("/{submission_id}", status_code=204)
async def delete_submission(
        submission_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    from app.services.admin import AdminSubmissionNotFound
    try:
        await admin_services.delete_admin_submission(db, submission_id)
    except AdminSubmissionNotFound:
        raise HTTPException(status_code=404, detail="Submission not found")
    return Response(status_code=204)

