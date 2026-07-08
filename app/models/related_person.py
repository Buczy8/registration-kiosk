from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import vehicle_type_enum

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.user import User


class RelatedPerson(Base):
    __tablename__ = "related_persons"
    __table_args__ = (Index("idx_related_persons_owner_user_id", "owner_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    guardian_relation: Mapped[str | None] = mapped_column(String(32))
    image_publication_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    vehicle_type: Mapped[str | None] = mapped_column(vehicle_type_enum)
    vehicle_brand: Mapped[str | None] = mapped_column(String(120))
    vehicle_model: Mapped[str | None] = mapped_column(String(120))
    vehicle_registration_number: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User] = relationship(back_populates="related_persons")
    submissions: Mapped[list[Submission]] = relationship(back_populates="related_person")
