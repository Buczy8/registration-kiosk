from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentAdminUser
from app.db.session import get_db
from app.schemas.admin import AdminUserListResponse
from app.schemas.auth import MessageResponse
from app.services import admin as admin_services

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


@router.get("", response_model=AdminUserListResponse)
async def get_users(
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    users, total_count = await admin_services.get_admin_users(db, limit, offset)

    return {
        "items": users,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{user_id}/lock", response_model=MessageResponse)
async def lock_user(
        user_id: UUID,
        admin: CurrentAdminUser,
        days: int = Query(7, ge=1, le=365, description="Na ile dni zablokować konto?"),
        db: AsyncSession = Depends(get_db),
):
    await admin_services.lock_user_account(db, user_id, admin.id, days)
    return {"message": f"Konto zablokowane na {days} dni."}


@router.patch("/{user_id}/unlock", response_model=MessageResponse)
async def unlock_user(
        user_id: UUID,
        admin: CurrentAdminUser,
        db: AsyncSession = Depends(get_db),
):
    await admin_services.unlock_user_account(db, user_id)
    return {"message": "Konto zostało odblokowane."}
