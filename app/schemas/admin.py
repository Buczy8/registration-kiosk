from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    ParticipantRole,
    PrintJobStatus,
    SubmissionMode,
    SubmissionStatus,
    VehicleType,
)

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generyczna koperta dla list admina."""

    items: list[T]
    total: int
    limit: int
    offset: int


class AdminUserListItem(BaseModel):
    """Uzytkownik w widoku admina. Bez password_hash i innych sekretow."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool
    failed_login_count: int
    locked_until: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminSubmissionListItem(BaseModel):
    """Zgloszenie w widoku listy admina (podsumowanie)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    mode: SubmissionMode
    participant_role: ParticipantRole
    vehicle_type: VehicleType
    start_number: int
    sequence_date: date
    status: SubmissionStatus
    user_id: UUID | None = None
    display_name: str | None = None
    created_at: datetime
    last_print_job_id: UUID | None = None
    last_print_status: PrintJobStatus | None = None
    last_print_at: datetime | None = None


class AdminSubmissionDetail(AdminSubmissionListItem):
    """Pelne dane zgloszenia dla admina."""

    form_id: UUID
    form_version: str
    filled_for_related_person_id: UUID | None = None
    payload_json: dict[str, Any]
    consents_json: dict[str, Any]
    declarations_accepted: bool
    signature_path: str | None = None
    signature_hash: str | None = None
    signed_at: datetime | None = None
    pdf_path: str | None = None
    updated_at: datetime


class AdminPrintJobSubmission(BaseModel):
    """Skrocone dane zgloszenia osadzone w print jobie."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_number: int
    sequence_date: date
    status: SubmissionStatus


class AdminPrintJobListItem(BaseModel):
    """Zadanie wydruku w widoku admina."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: UUID
    status: PrintJobStatus
    copies: int
    attempts: int
    last_error: str | None = None
    idempotency_key: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    submission: AdminPrintJobSubmission | None = None


AdminUserListResponse = PaginatedResponse[AdminUserListItem]
AdminSubmissionListResponse = PaginatedResponse[AdminSubmissionListItem]
AdminPrintJobListResponse = PaginatedResponse[AdminPrintJobListItem]


class AdminDashboardStats(BaseModel):
    """Statystyki panelu admina dla wybranego dnia (sequence_date)."""

    sequence_date: date
    total_submissions: int
    submitted_count: int
    print_queued_count: int
    print_done_count: int
    print_failed_count: int
    guest_count: int
    account_count: int
    last_start_number: int | None = None


class AdminSystemStatus(BaseModel):
    checked_at: datetime
    api_ok: bool
    db_ok: bool
