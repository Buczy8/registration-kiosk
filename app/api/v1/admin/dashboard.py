from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.db.session import get_db
from app.schemas.admin import AdminDashboardStats
from app.services import admin as admin_services

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


@router.get("", response_model=AdminDashboardStats)
async def get_dashboard_stats(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        sequence_date: date | None = Query(None),
):
    target_date = sequence_date or date.today()
    return await admin_services.get_admin_dashboard_stats(db, target_date)
