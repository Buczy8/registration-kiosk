from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.submission import Submission


class Form(Base):
    __tablename__ = "forms"
    __table_args__ = (
        Index(
            "uq_forms_one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pdf_template_path: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    submissions: Mapped[list[Submission]] = relationship(back_populates="form")
