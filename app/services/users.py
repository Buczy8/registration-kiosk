from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_password
from app.models.user import User, UserProfile
from app.schemas.auth import RegisterRequest


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    normalized_email = email.strip().lower()
    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: RegisterRequest) -> User:
    user = User(
        email=data.email.strip().lower(),
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )
    db.add(user)

    try:
        await db.flush()
        profile = UserProfile(user_id=user.id, vehicles_json={})
        db.add(profile)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(user)
    return user


def is_account_locked(user: User) -> bool:
    if user.locked_until is None:
        return False
    return user.locked_until > datetime.now(UTC)


async def record_failed_login(db: AsyncSession, user: User, settings: Settings) -> None:
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(failed_login_count=User.failed_login_count + 1)
    )
    await db.refresh(user)

    if user.failed_login_count >= settings.login_max_attempts:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.login_lockout_minutes)
        await db.commit()


async def reset_failed_login(db: AsyncSession, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    await db.commit()

