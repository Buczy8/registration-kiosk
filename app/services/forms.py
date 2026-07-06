from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form import Form


async def get_active_form(db: AsyncSession) -> Form:
    result = await db.execute(
        select(Form).where(Form.is_active.is_(True))
    )
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active form not found",
        )
    return form
