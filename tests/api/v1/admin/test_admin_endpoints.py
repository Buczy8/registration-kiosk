from datetime import date, datetime, timedelta, UTC
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.deps import KIOSK_TOKEN_HEADER
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User, UserProfile
from app.models.submission import Submission
from app.models.print_job import PrintJob
from app.models.enums import (
    ParticipantRole,
    PrintJobStatus,
    SubmissionMode,
    SubmissionStatus,
    VehicleType,
)
from main import app
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN


class _FakeScalars:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class _FakeResult:
    def __init__(self, value=None, items=None):
        self._value = value
        self._items = items or []

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value

    def scalars(self):
        return _FakeScalars(self._items)


class _FakeAdminDb:
    def __init__(self, users=None, submissions=None, print_jobs=None):
        self.users = list(users or [])
        self.submissions = list(submissions or [])
        self.print_jobs = list(print_jobs or [])
        self.added = []
        self.commits = 0

    async def execute(self, statement, params=None):
        sql = str(statement).lower()

        # Obsługa zapytań zliczających (count)
        if "count(" in sql or "count(1)" in sql:
            if "submissions" in sql:
                return _FakeResult(value=len(self.submissions))
            if "print_job" in sql:
                return _FakeResult(value=len(self.print_jobs))
            if "users" in sql:
                return _FakeResult(value=len(self.users))

        # Obsługa zapytań pobierających dane (select)
        if "from users" in sql:
            if "where users.id" in sql or "where users.id =" in sql:
                expected_id = next(iter(statement.compile().params.values()), None)
                if expected_id:
                    user = next((u for u in self.users if str(u.id) == str(expected_id)), None)
                    return _FakeResult(value=user)
                return _FakeResult(value=self.users[0] if self.users else None)
            return _FakeResult(items=self.users)

        if "from submissions" in sql:
            if "where submissions.id" in sql:
                return _FakeResult(value=self.submissions[0] if self.submissions else None)
            return _FakeResult(items=self.submissions)

        if "from print_job" in sql:
            return _FakeResult(items=self.print_jobs)

        return _FakeResult()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1


def _settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
    )


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_settings] = lambda: _settings()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_db, None)


def _user(*, is_superuser=False) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email="admin@example.com" if is_superuser else "user@example.com",
        password_hash="super-secret-hash",
        is_active=True,
        is_superuser=is_superuser,
        failed_login_count=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )


def _submission() -> Submission:
    now = datetime.now(UTC)
    return Submission(
        id=uuid4(),
        form_id=uuid4(),
        form_version="1.0",
        mode=SubmissionMode.GUEST,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=1,
        sequence_date=date.today(),
        payload_json={},
        consents_json={},
        declarations_accepted=True,
        status=SubmissionStatus.SUBMITTED,
        created_at=now,
        updated_at=now,
    )


def _print_job(submission: Submission | None = None) -> PrintJob:
    return PrintJob(
        id=uuid4(),
        submission_id=submission.id if submission else uuid4(),
        copies=1,
        status=PrintJobStatus.QUEUED,
        attempts=0,
        last_error=None,
        idempotency_key=None,
        queued_at=datetime.now(UTC),
        started_at=None,
        finished_at=None,
        submission=submission,
    )


def _auth_headers(user_id) -> dict[str, str]:
    token = create_access_token(user_id, _settings())
    return {
        KIOSK_TOKEN_HEADER: TEST_KIOSK_TOKEN,
        "Authorization": f"Bearer {token}"
    }


def test_admin_endpoints_reject_normal_user(client: TestClient):
    user = _user(is_superuser=False)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[user])

    response = client.get("/api/v1/admin/submissions", headers=_auth_headers(user.id))

    assert response.status_code == 403


def test_admin_endpoints_accept_superuser(client: TestClient):
    admin = _user(is_superuser=True)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[admin])

    response = client.get("/api/v1/admin/submissions", headers=_auth_headers(admin.id))

    assert response.status_code == 200


def test_get_submissions_returns_paginated_list(client: TestClient):
    admin = _user(is_superuser=True)
    sub = _submission()
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[admin], submissions=[sub])

    response = client.get("/api/v1/admin/submissions?limit=10&offset=0", headers=_auth_headers(admin.id))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(sub.id)


def test_queue_submission_for_print_updates_status(client: TestClient, monkeypatch):
    admin = _user(is_superuser=True)
    sub = _submission()
    db = _FakeAdminDb(users=[admin], submissions=[sub])
    app.dependency_overrides[get_db] = lambda: db

    async def _fake_generate_submission_pdf(_db, submission_id):
        assert submission_id == sub.id
        return sub, b"%PDF-1.4 test"

    monkeypatch.setattr(
        "app.services.pdf.generate_submission_pdf",
        _fake_generate_submission_pdf,
    )

    response = client.post(f"/api/v1/admin/submissions/{sub.id}/print", headers=_auth_headers(admin.id))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert db.commits == 1
    assert len(db.added) == 1
    assert sub.status == SubmissionStatus.PRINT_DONE
    assert db.added[0].status == PrintJobStatus.DONE


def test_get_submission_pdf_returns_pdf_without_print_job(client: TestClient, monkeypatch):
    admin = _user(is_superuser=True)
    sub = _submission()
    db = _FakeAdminDb(users=[admin], submissions=[sub])
    app.dependency_overrides[get_db] = lambda: db

    async def _fake_generate_submission_pdf(_db, submission_id):
        assert submission_id == sub.id
        return sub, b"%PDF-1.4 preview"

    monkeypatch.setattr(
        "app.services.pdf.generate_submission_pdf",
        _fake_generate_submission_pdf,
    )

    response = client.get(
        f"/api/v1/admin/submissions/{sub.id}/pdf",
        headers=_auth_headers(admin.id),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert db.commits == 0
    assert len(db.added) == 0


def test_get_dashboard_returns_day_stats(client: TestClient, monkeypatch):
    admin = _user(is_superuser=True)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[admin])

    async def _fake_dashboard_stats(_db, sequence_date):
        return {
            "sequence_date": sequence_date,
            "total_submissions": 5,
            "submitted_count": 2,
            "print_queued_count": 1,
            "print_done_count": 1,
            "print_failed_count": 1,
            "guest_count": 3,
            "account_count": 2,
            "last_start_number": 42,
        }

    monkeypatch.setattr(
        "app.services.admin.get_admin_dashboard_stats",
        _fake_dashboard_stats,
    )

    response = client.get("/api/v1/admin/dashboard", headers=_auth_headers(admin.id))

    assert response.status_code == 200
    data = response.json()
    assert data["total_submissions"] == 5
    assert data["guest_count"] == 3
    assert data["account_count"] == 2
    assert data["last_start_number"] == 42
    assert data["print_done_count"] == 1


def test_lock_user_account(client: TestClient):
    admin = _user(is_superuser=True)
    target_user = _user(is_superuser=False)
    db = _FakeAdminDb(users=[target_user, admin])
    app.dependency_overrides[get_db] = lambda: db

    response = client.patch(f"/api/v1/admin/users/{target_user.id}/lock?days=5", headers=_auth_headers(admin.id))

    assert response.status_code == 200
    assert db.commits == 1
    assert target_user.locked_until is not None
    expected_lock = datetime.now(UTC) + timedelta(days=5)
    assert abs((target_user.locked_until - expected_lock).total_seconds()) < 5


def test_unlock_user_account(client: TestClient):
    admin = _user(is_superuser=True)
    target_user = _user(is_superuser=False)
    target_user.locked_until = datetime.now(UTC) + timedelta(days=3)
    target_user.failed_login_count = 5
    db = _FakeAdminDb(users=[target_user, admin])
    app.dependency_overrides[get_db] = lambda: db

    response = client.patch(
        f"/api/v1/admin/users/{target_user.id}/unlock",
        headers=_auth_headers(admin.id),
    )

    assert response.status_code == 200
    assert db.commits == 1
    assert target_user.locked_until is None
    assert target_user.failed_login_count == 0


def test_admin_cannot_lock_own_account(client: TestClient):
    admin = _user(is_superuser=True)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[admin])

    response = client.patch(f"/api/v1/admin/users/{admin.id}/lock", headers=_auth_headers(admin.id))

    assert response.status_code == 400


def test_get_users_does_not_leak_password_hash(client: TestClient):
    admin = _user(is_superuser=True)
    target = _user(is_superuser=False)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[admin, target])

    response = client.get("/api/v1/admin/users", headers=_auth_headers(admin.id))

    assert response.status_code == 200
    body = response.text
    assert "password_hash" not in body
    assert "super-secret-hash" not in body
    data = response.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert "password_hash" not in item
        assert "email" in item


def test_lock_user_rejects_non_positive_days(client: TestClient):
    admin = _user(is_superuser=True)
    target = _user(is_superuser=False)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(users=[target, admin])

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/lock?days=0",
        headers=_auth_headers(admin.id),
    )

    assert response.status_code == 422


def test_get_print_jobs_returns_paginated_list(client: TestClient):
    admin = _user(is_superuser=True)
    sub = _submission()
    job = _print_job(sub)
    app.dependency_overrides[get_db] = lambda: _FakeAdminDb(
        users=[admin], print_jobs=[job]
    )

    response = client.get("/api/v1/admin/print-jobs", headers=_auth_headers(admin.id))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(job.id)
    assert data["items"][0]["status"] == PrintJobStatus.QUEUED.value
    assert data["items"][0]["submission"]["start_number"] == sub.start_number
