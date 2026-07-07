import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import Settings
from app.models.user import User, UserProfile
from app.schemas.auth import RegisterRequest
from app.services.users import (
    create_user,
    get_user_by_email,
    is_account_locked,
    record_failed_login,
)
from tests.conftest import TEST_JWT_SECRET, TEST_KIOSK_TOKEN


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeUsersDb:
    def __init__(self, users=None):
        self.users = list(users or [])
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.refreshed = []

    async def execute(self, statement, params=None):
        compiled = statement.compile()
        sql = str(compiled)
        bound = compiled.params

        if "lower(users.email)" in sql:
            expected = bound.get("lower_1", "")
            match = next((u for u in self.users if u.email.lower() == expected), None)
            return _FakeResult(match)
        return _FakeResult(None)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, User):
            self.users.append(obj)

    async def flush(self):
        for obj in self.added:
            if isinstance(obj, User) and getattr(obj, "id", None) is None:
                obj.id = uuid4()

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        self.refreshed.append(obj)


def _settings() -> Settings:
    return Settings(
        kiosk_token=TEST_KIOSK_TOKEN,
        jwt_secret_key=TEST_JWT_SECRET,
        login_max_attempts=3,
        login_lockout_minutes=15,
    )


def _user(*, failed_login_count: int = 0, locked_until=None) -> User:
    return User(
        id=uuid4(),
        email="jan.kowalski@example.com",
        password_hash="hash",
        first_name="Jan",
        last_name="Kowalski",
        phone=None,
        is_active=True,
        failed_login_count=failed_login_count,
        locked_until=locked_until,
    )


def test_create_user_saves_user_and_profile_in_same_transaction():
    db = _FakeUsersDb()
    data = RegisterRequest(
        email="Jan.Kowalski@Example.com",
        password="StrongPass1",
        first_name="Jan",
        last_name="Kowalski",
        phone="+48 123 123 123",
    )

    user = asyncio.run(create_user(db, data))

    assert db.committed is True
    assert isinstance(db.added[0], User)
    assert isinstance(db.added[1], UserProfile)
    assert db.added[0].email == "jan.kowalski@example.com"
    assert db.added[1].user_id == user.id
    assert db.refreshed == [user]


def test_get_user_by_email_is_case_insensitive():
    existing = _user()
    db = _FakeUsersDb([existing])

    result = asyncio.run(get_user_by_email(db, "JAN.KOWALSKI@EXAMPLE.COM"))

    assert result is existing


def test_record_failed_login_locks_after_threshold_from_settings():
    user = _user(failed_login_count=2, locked_until=None)
    db = _FakeUsersDb([user])

    asyncio.run(record_failed_login(db, user, _settings()))

    assert user.failed_login_count == 3
    assert user.locked_until is not None
    assert db.committed is True


def test_is_account_locked_false_after_locked_until_expired():
    user = _user(locked_until=datetime.now(UTC) - timedelta(minutes=1))

    assert is_account_locked(user) is False

