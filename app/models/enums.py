import enum

from sqlalchemy.types import Enum as SAEnum


class SubmissionMode(str, enum.Enum):
    GUEST = "guest"
    ACCOUNT = "account"


class ParticipantRole(str, enum.Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"
    LEGAL_GUARDIAN = "legal_guardian"


class VehicleType(str, enum.Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    GOKART = "gokart"


class SubmissionStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    PRINT_QUEUED = "print_queued"
    PRINT_DONE = "print_done"
    PRINT_FAILED = "print_failed"


class PrintJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PRINTING = "printing"
    DONE = "done"
    FAILED = "failed"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


submission_mode_enum = SAEnum(
    SubmissionMode,
    name="submission_mode",
    values_callable=_enum_values,
    create_type=False,
)
participant_role_enum = SAEnum(
    ParticipantRole,
    name="participant_role",
    values_callable=_enum_values,
    create_type=False,
)
vehicle_type_enum = SAEnum(
    VehicleType,
    name="vehicle_type",
    values_callable=_enum_values,
    create_type=False,
)
submission_status_enum = SAEnum(
    SubmissionStatus,
    name="submission_status",
    values_callable=_enum_values,
    create_type=False,
)
print_job_status_enum = SAEnum(
    PrintJobStatus,
    name="print_job_status",
    values_callable=_enum_values,
    create_type=False,
)
