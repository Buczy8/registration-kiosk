from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.form import Form


def get_active_form(db: Session) -> Form:
    form = db.execute(
        select(Form).where(Form.is_active.is_(True))
    ).scalar_one_or_none()
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active form not found",
        )
    return form
