from __future__ import annotations

from collections.abc import AsyncGenerator
import uuid

from app.models.form import Form
from app.models.submission import Submission


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class FakeAsyncDb:
    """Minimal async session fake for single-value execute() results."""

    def __init__(self, value):
        self._value = value
        self.last_statement = None
        self.last_params = None

    async def execute(self, statement, params=None):
        self.last_statement = statement
        self.last_params = params
        return FakeResult(self._value)


class FakeAsyncSubmissionDb:
    """Async session fake for submission create/read flows."""

    def __init__(
        self,
        form: Form,
        *,
        start_number: int = 42,
        existing_submission: Submission | None = None,
        commit_raises: Exception | None = None,
    ):
        self.form = form
        self.start_number = start_number
        self.existing_submission = existing_submission
        self.commit_raises = commit_raises
        self.last_statement = None
        self.last_params = None
        self.added: list[Submission] = []
        self.committed = False
        self.rolled_back = False
        self.refreshed: list[Submission] = []
        self._submission: Submission | None = None

    async def execute(self, statement, params=None):
        self.last_statement = statement
        self.last_params = params
        if "next_start_number" in str(statement):
            return FakeResult(self.start_number)
        if "FROM submissions" in str(statement):
            return FakeResult(self.existing_submission)
        return FakeResult(self.form)

    def add(self, submission: Submission) -> None:
        self.added.append(submission)
        self._submission = submission

    async def flush(self) -> None:
        for submission in self.added:
            if submission.id is None:
                submission.id = uuid.uuid4()

    async def commit(self) -> None:
        if self.commit_raises is not None:
            raise self.commit_raises
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, submission: Submission) -> None:
        if submission.id is None:
            submission.id = uuid.uuid4()
        self.refreshed.append(submission)


class FakeHealthyDb:
    async def execute(self, _statement):
        return None


def async_get_db_override(db):
    async def override_get_db() -> AsyncGenerator:
        yield db

    return override_get_db
