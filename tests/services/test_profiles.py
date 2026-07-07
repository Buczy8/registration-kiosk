import asyncio
from datetime import date
from uuid import uuid4

from app.models.enums import ParticipantRole, VehicleType
from app.models.user import User, UserProfile
from app.services.profiles import get_form_prefill, update_profile_from_submission


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeProfilesDb:
    def __init__(self, profiles=None):
        self.profiles = list(profiles or [])
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, statement, params=None):
        compiled = statement.compile()
        expected_user_id = next(iter(compiled.params.values()), None)
        profile = next(
            (p for p in self.profiles if str(p.user_id) == str(expected_user_id)),
            None,
        )
        return _FakeResult(profile)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, UserProfile):
            self.profiles.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


def _user() -> User:
    return User(
        id=uuid4(),
        email="jan.kowalski@example.com",
        password_hash="hash",
        first_name=None,
        last_name=None,
        phone=None,
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )


def _profile(user_id, *, vehicles_json=None) -> UserProfile:
    return UserProfile(
        user_id=user_id,
        address=None,
        birth_date=None,
        document_number=None,
        ice_name=None,
        ice_phone=None,
        vehicles_json=vehicles_json or {},
    )


def test_prefill_with_empty_profile_returns_null_fields():
    user = _user()
    db = _FakeProfilesDb(profiles=[_profile(user.id)])

    prefill = asyncio.run(
        get_form_prefill(db, user, ParticipantRole.DRIVER, VehicleType.CAR)
    )

    assert prefill.first_name is None
    assert prefill.last_name is None
    assert prefill.address is None
    assert prefill.birth_date is None
    assert prefill.document_number is None
    assert prefill.vehicle is None


def test_prefill_with_saved_car_returns_car_not_motorcycle():
    user = _user()
    profile = _profile(
        user.id,
        vehicles_json={
            "car": {"brand_model": "BMW M3", "registration_number": "WX 12345"},
            "motorcycle": {"brand_model": "Yamaha MT", "registration_number": "KR 9999"},
        },
    )
    db = _FakeProfilesDb(profiles=[profile])

    prefill = asyncio.run(
        get_form_prefill(db, user, ParticipantRole.DRIVER, VehicleType.CAR)
    )

    assert prefill.vehicle is not None
    assert prefill.vehicle.brand_model == "BMW M3"
    assert prefill.vehicle.registration_number == "WX 12345"


def test_prefill_legal_guardian_returns_minimal_payload():
    user = _user()
    profile = _profile(user.id)
    profile.address = "Warszawa"
    profile.document_number = "ABC123"
    db = _FakeProfilesDb(profiles=[profile])

    prefill = asyncio.run(
        get_form_prefill(db, user, ParticipantRole.LEGAL_GUARDIAN, VehicleType.CAR)
    )

    assert prefill.address is None
    assert prefill.document_number is None


def test_update_profile_saves_vehicles_json_per_type():
    user = _user()
    profile = _profile(user.id)
    db = _FakeProfilesDb(profiles=[profile])

    asyncio.run(
        update_profile_from_submission(
            db,
            user,
            payload={
                "first_name": "Jan",
                "last_name": "Kowalski",
                "phone": "+48 500 600 700",
                "residence_address": "Warszawa",
                "birth_date": date(1990, 1, 1),
                "document_number": "ABC123",
                "vehicle_brand_model": "BMW M3",
                "vehicle_registration_number": "WX 12345",
            },
            vehicle_type=VehicleType.CAR,
        )
    )

    assert profile.vehicles_json["car"]["brand_model"] == "BMW M3"
    assert profile.vehicles_json["car"]["registration_number"] == "WX 12345"


def test_update_car_does_not_overwrite_motorcycle():
    user = _user()
    profile = _profile(
        user.id,
        vehicles_json={
            "motorcycle": {"brand_model": "Yamaha MT", "registration_number": "KR 9999"}
        },
    )
    db = _FakeProfilesDb(profiles=[profile])

    asyncio.run(
        update_profile_from_submission(
            db,
            user,
            payload={
                "vehicle_brand_model": "BMW M3",
                "vehicle_registration_number": "WX 12345",
            },
            vehicle_type=VehicleType.CAR,
        )
    )

    assert profile.vehicles_json["car"]["brand_model"] == "BMW M3"
    assert profile.vehicles_json["motorcycle"]["brand_model"] == "Yamaha MT"

