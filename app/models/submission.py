from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    ParticipantRole,
    SubmissionMode,
    SubmissionStatus,
    VehicleType,
    participant_role_enum,
    submission_mode_enum,
    submission_status_enum,
    vehicle_type_enum,
)

if TYPE_CHECKING:
    from app.models.form import Form
    from app.models.print_job import PrintJob
    from app.models.related_person import RelatedPerson
    from app.models.user import User


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("sequence_date", "start_number", name="uq_submissions_sequence_date_start_number"),
        CheckConstraint(
            f"(mode = '{SubmissionMode.GUEST.value}' AND user_id IS NULL "
            f"AND filled_for_related_person_id IS NULL) "
            f"OR (mode = '{SubmissionMode.ACCOUNT.value}' AND user_id IS NOT NULL)",
            name="chk_submissions_account_requires_user",
        ),
        CheckConstraint(
            f"filled_for_related_person_id IS NULL OR mode = '{SubmissionMode.ACCOUNT.value}'",
            name="chk_submissions_related_person_requires_account",
        ),
        Index("idx_submissions_created_at", "created_at"),
        Index("idx_submissions_status", "status"),
        Index("idx_submissions_user_id", "user_id"),
        Index("idx_submissions_filled_for_related_person_id", "filled_for_related_person_id"),
        Index("idx_submissions_sequence_date", "sequence_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    form_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forms.id"), nullable=False
    )
    form_version: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    filled_for_related_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("related_persons.id", ondelete="SET NULL")
    )
    mode: Mapped[SubmissionMode] = mapped_column(submission_mode_enum, nullable=False)
    participant_role: Mapped[ParticipantRole] = mapped_column(participant_role_enum, nullable=False)
    vehicle_type: Mapped[VehicleType] = mapped_column(vehicle_type_enum, nullable=False)
    start_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_date: Mapped[date] = mapped_column(Date, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    consents_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    declarations_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    signature_path: Mapped[str | None] = mapped_column(Text)
    signature_hash: Mapped[str | None] = mapped_column(String(128))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SubmissionStatus] = mapped_column(
        submission_status_enum,
        nullable=False,
        server_default=text("'submitted'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    form: Mapped[Form] = relationship(back_populates="submissions")
    user: Mapped[User | None] = relationship(back_populates="submissions")
    related_person: Mapped[RelatedPerson | None] = relationship(back_populates="submissions")
    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="submission")
