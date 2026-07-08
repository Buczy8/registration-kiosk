"""
E2E scenario: Guardian registers two dependents and submits forms for both.
Validates that each dependent gets their own start_number and submission.
"""

import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.enums import ParticipantRole, SubmissionMode, VehicleType
from app.models.form import Form
from app.models.related_person import RelatedPerson
from app.models.user import User, UserProfile
from app.schemas.related_person import RelatedPersonCreate
from app.services.related_persons import create_related_person, list_related_persons
from app.services.submissions import create_account_submission_for_related_person
from app.schemas.submission import AccountSubmissionCreate
from tests.fixtures.signature_samples import sample_signature_base64


def related_person_create_data(**overrides):
    data = {
        "first_name": "Jan",
        "last_name": "Nowak",
        "birth_date": date(2010, 1, 1),
        "guardian_relation": "parent",
        "image_publication_consent": True,
        "vehicle_type": VehicleType.CAR,
        "vehicle_brand": "Toyota",
        "vehicle_model": "Yaris",
        "vehicle_registration_number": "LBI12345",
    }
    data.update(overrides)
    return data


@pytest.fixture
def guardian_user() -> User:
    """Create a guardian user."""
    return User(
        id=uuid.uuid4(),
        email="opiekun@example.com",
        password_hash="hash",
        first_name="Anna",
        last_name="Nowak",
        phone="123456789",
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )


@pytest.fixture
def guardian_profile(guardian_user: User) -> UserProfile:
    """Create a profile for the guardian."""
    return UserProfile(
        user_id=guardian_user.id,
        address="ul. Testowa 1",
        birth_date=date(1985, 5, 15),
        document_number="ABC123456",
        ice_name="Emergency Contact",
        ice_phone="999999999",
        vehicles_json={},
    )


@pytest.fixture
def active_form() -> Form:
    """Create an active form."""
    return Form(
        id=uuid.uuid4(),
        code="participant-universal",
        name="Oświadczenie uczestnika",
        version="2.0",
        schema_json={
            "required": ["first_name", "last_name", "document_number"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "document_number": {"type": "string"},
            },
        },
        pdf_template_path="templates/forms/participant-v2.pdf",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_e2e_guardian_two_dependents(
    async_session: AsyncSession,
    guardian_user: User,
    guardian_profile: UserProfile,
    active_form: Form,
    kiosk_settings_with_storage: Settings,
):
    """
    E2E: Guardian creates two dependents and submits forms for both.
    Validates:
    1. Each dependent is created and listed with correct ownership
    2. Each submission gets its own start_number
    3. Guardian profile is NOT updated after submissions
    4. Each dependent has a separate submission record
    """
    async_session.add_all([active_form, guardian_user, guardian_profile])
    await async_session.flush()

    dependent1_data = RelatedPersonCreate(
        **related_person_create_data(
            first_name="Michał",
            last_name="Nowak",
            birth_date=date(2010, 3, 20),
            vehicle_type=VehicleType.CAR,
            vehicle_brand="Ford",
            vehicle_model="Focus",
            vehicle_registration_number="LBL1234A",
        )
    )
    dependent2_data = RelatedPersonCreate(
        **related_person_create_data(
            first_name="Katarzyna",
            last_name="Nowak",
            birth_date=date(2012, 7, 15),
            vehicle_type=VehicleType.MOTORCYCLE,
            vehicle_brand="Kawasaki",
            vehicle_model="Ninja",
            vehicle_registration_number="LBL8899K",
        )
    )

    dependent1 = await create_related_person(async_session, guardian_user.id, dependent1_data)
    await async_session.flush()

    dependent2 = await create_related_person(async_session, guardian_user.id, dependent2_data)
    await async_session.flush()

    persons = await list_related_persons(async_session, guardian_user.id)
    assert len(persons) == 2
    assert persons[1].first_name == "Michał"
    assert persons[0].first_name == "Katarzyna"

    submission1_data = AccountSubmissionCreate(
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        payload_json={
            "first_name": "Michał",
            "last_name": "Nowak",
            "document_number": "ABC123456",
        },
        consents_json={"rodo": True},
        declarations_accepted=True,
        signature_image_base64=sample_signature_base64(),
    )

    submission1 = await create_account_submission_for_related_person(
        db=async_session,
        current_user_id=guardian_user.id,
        related_person_id=dependent1.id,
        data=submission1_data,
        settings=kiosk_settings_with_storage,
    )
    await async_session.refresh(submission1)

    assert submission1.id is not None
    assert submission1.user_id == guardian_user.id
    assert submission1.filled_for_related_person_id == dependent1.id
    assert submission1.mode == SubmissionMode.ACCOUNT
    assert submission1.participant_role == ParticipantRole.DRIVER
    assert submission1.start_number == 1

    submission2_data = AccountSubmissionCreate(
        participant_role=ParticipantRole.PASSENGER,
        vehicle_type=VehicleType.MOTORCYCLE,
        payload_json={
            "first_name": "Katarzyna",
            "last_name": "Nowak",
            "document_number": "XYZ987654",
        },
        consents_json={"rodo": True},
        declarations_accepted=True,
        signature_image_base64=sample_signature_base64(),
    )

    submission2 = await create_account_submission_for_related_person(
        db=async_session,
        current_user_id=guardian_user.id,
        related_person_id=dependent2.id,
        data=submission2_data,
        settings=kiosk_settings_with_storage,
    )
    await async_session.refresh(submission2)

    assert submission2.id is not None
    assert submission2.user_id == guardian_user.id
    assert submission2.filled_for_related_person_id == dependent2.id
    assert submission2.mode == SubmissionMode.ACCOUNT
    assert submission2.participant_role == ParticipantRole.PASSENGER
    assert submission2.start_number == 2
    assert submission2.sequence_date == submission1.sequence_date

    assert submission1.start_number != submission2.start_number
    assert submission1.id != submission2.id

    await async_session.refresh(guardian_profile)
    assert guardian_profile.vehicles_json == {}


@pytest.mark.asyncio
async def test_guardian_cannot_submit_for_other_users_dependent(
    async_session: AsyncSession,
    guardian_user: User,
    active_form: Form,
    kiosk_settings_with_storage: Settings,
):
    """
    Security: Guardian cannot submit form for another user's dependent.
    """
    other_user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        password_hash="hash",
        first_name="Zbigniew",
        last_name="Kowalski",
        phone=None,
        is_active=True,
        failed_login_count=0,
        locked_until=None,
    )
    async_session.add_all([active_form, guardian_user, other_user])
    await async_session.flush()

    dependent_data = RelatedPersonCreate(
        **related_person_create_data(
            first_name="Szymon",
            last_name="Kowalski",
            birth_date=None,
        )
    )

    dependent = await create_related_person(async_session, other_user.id, dependent_data)
    await async_session.flush()

    submission_data = AccountSubmissionCreate(
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        payload_json={
            "first_name": "Szymon",
            "last_name": "Kowalski",
            "document_number": "ABC123456",
        },
        consents_json={"rodo": True},
        declarations_accepted=True,
        signature_image_base64=sample_signature_base64(),
    )

    from app.services.related_persons import RelatedPersonNotOwnedByUser

    with pytest.raises(RelatedPersonNotOwnedByUser):
        await create_account_submission_for_related_person(
            db=async_session,
            current_user_id=guardian_user.id,
            related_person_id=dependent.id,
            data=submission_data,
            settings=kiosk_settings_with_storage,
        )


@pytest.mark.asyncio
async def test_guardian_related_person_submission_updates_guardian_profile(
    async_session: AsyncSession,
    guardian_user: User,
    guardian_profile: UserProfile,
    active_form: Form,
    kiosk_settings_with_storage: Settings,
):
    """Submitting for a dependent stores guardian profile data for future prefill."""
    async_session.add_all([active_form, guardian_user, guardian_profile])
    await async_session.flush()

    dependent = await create_related_person(
        async_session,
        guardian_user.id,
        RelatedPersonCreate(
            **related_person_create_data(
                first_name="Michał",
                last_name="Nowak",
                birth_date=None,
                vehicle_brand=None,
            )
        ),
    )
    await async_session.flush()

    submission_data = AccountSubmissionCreate(
        participant_role=ParticipantRole.LEGAL_GUARDIAN,
        vehicle_type=VehicleType.CAR,
        payload_json={
            "first_name": "Anna",
            "last_name": "Nowak",
            "document_number": "ABC123456",
            "residence_address": "ul. Nowa 7",
            "pesel": "12345678901",
            "emergency_contact_name": "Jan Nowak",
            "emergency_contact_phone": "600700800",
            "guardian_relation": "parent",
            "minor_first_name": "Michał",
            "minor_last_name": "Nowak",
            "vehicle_brand": "Ford",
            "vehicle_model": "Focus",
            "vehicle_registration_number": "LBL1234A",
        },
        consents_json={"image_publication": True},
        declarations_accepted=True,
        signature_image_base64=sample_signature_base64(),
    )

    await create_account_submission_for_related_person(
        db=async_session,
        current_user_id=guardian_user.id,
        related_person_id=dependent.id,
        data=submission_data,
        settings=kiosk_settings_with_storage,
        current_user=guardian_user,
    )

    await async_session.refresh(guardian_profile)
    assert guardian_profile.address == "ul. Nowa 7"
    assert guardian_profile.pesel == "12345678901"
    assert guardian_profile.ice_name == "Jan Nowak"
    assert guardian_profile.ice_phone == "600700800"

    await async_session.refresh(dependent)
    assert dependent.vehicle_brand == "Ford"
    assert dependent.vehicle_model == "Focus"
    assert dependent.vehicle_registration_number == "LBL1234A"

    related_persons = await list_related_persons(async_session, guardian_user.id)
    assert related_persons[0].vehicle_brand == "Ford"
