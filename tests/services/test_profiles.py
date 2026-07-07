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


def _profile(user_id, **overrides) -> UserProfile:
    defaults = {
        "user_id": user_id,
        "address": None,
        "birth_date": None,
        "document_number": None,
        "pesel": None,
        "id_card_series": None,
        "id_card_number": None,
        "ice_name": None,
        "ice_phone": None,
        "last_participant_role": None,
        "last_vehicle_type": None,
        "vehicles_json": {},
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


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
    assert prefill.pesel is None
    assert prefill.ice_name is None
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


def test_prefill_returns_ice_and_identity_fields():
    user = _user()
    profile = _profile(
        user.id,
        pesel="12345678901",
        ice_name="Anna Kowalska",
        ice_phone="+48 700 800 900",
        vehicles_json={
            "car": {"brand_model": "BMW M3", "registration_number": "WX 12345"},
        },
    )
    db = _FakeProfilesDb(profiles=[profile])

    prefill = asyncio.run(
        get_form_prefill(db, user, ParticipantRole.DRIVER, VehicleType.CAR)
    )

    assert prefill.pesel == "12345678901"
    assert prefill.ice_name == "Anna Kowalska"
    assert prefill.ice_phone == "+48 700 800 900"


def test_prefill_legal_guardian_returns_minimal_payload():
    user = _user()
    profile = _profile(
        user.id,
        address="Warszawa",
        pesel="12345678901",
        ice_name="Anna",
    )
    db = _FakeProfilesDb(profiles=[profile])

    prefill = asyncio.run(
        get_form_prefill(db, user, ParticipantRole.LEGAL_GUARDIAN, VehicleType.CAR)
    )

    assert prefill.address is None
    assert prefill.pesel is None
    assert prefill.ice_name is None


def test_update_profile_saves_ice_pesel_and_vehicle():
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
                "pesel": "12345678901",
                "emergency_contact_name": "Anna Kowalska",
                "emergency_contact_phone": "+48 700 800 900",
                "vehicle_brand": "BMW",
                "vehicle_model": "M3",
                "vehicle_registration_number": "WX 12345",
            },
            vehicle_type=VehicleType.CAR,
            role=ParticipantRole.DRIVER,
        )
    )

    assert user.first_name == "Jan"
    assert profile.pesel == "12345678901"
    assert profile.ice_name == "Anna Kowalska"
    assert profile.ice_phone == "+48 700 800 900"
    assert profile.last_participant_role == "driver"
    assert profile.last_vehicle_type == "car"
    assert profile.vehicles_json["car"]["brand_model"] == "BMW M3"


def test_update_profile_saves_id_card_fields():
    user = _user()
    profile = _profile(user.id)
    db = _FakeProfilesDb(profiles=[profile])

    asyncio.run(
        update_profile_from_submission(
            db,
            user,
            payload={
                "id_card_series": "ABC",
                "id_card_number": "123456",
                "vehicle_brand": "Yamaha",
                "vehicle_model": "MT-07",
                "vehicle_registration_number": "KR 9999",
            },
            vehicle_type=VehicleType.MOTORCYCLE,
            role=ParticipantRole.PASSENGER,
        )
    )

    assert profile.id_card_series == "ABC"
    assert profile.id_card_number == "123456"
    assert profile.last_participant_role == "passenger"
    assert profile.last_vehicle_type == "motorcycle"


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
                "vehicle_brand": "BMW",
                "vehicle_model": "M3",
                "vehicle_registration_number": "WX 12345",
            },
            vehicle_type=VehicleType.CAR,
            role=ParticipantRole.DRIVER,
        )
    )

    assert profile.vehicles_json["car"]["brand_model"] == "BMW M3"
    assert profile.vehicles_json["motorcycle"]["brand_model"] == "Yamaha MT"
