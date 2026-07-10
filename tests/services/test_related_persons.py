"""
Tests for related_persons service.

Domain: RelatedPerson aggregate
- Ownership validation
- Form preview queries
- Creation with invariant checks
"""

from datetime import date, datetime
from uuid import uuid4
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ParticipantRole, SubmissionMode, VehicleType
from app.models.related_person import RelatedPerson
from app.models.submission import Submission
from app.schemas.related_person import (
    FormPreview,
    RelatedPersonCreate,
    RelatedPersonWithPreview,
)
from app.services.related_persons import (
    RelatedPersonNotFound,
    RelatedPersonNotOwnedByUser,
    create_related_person,
    get_form_preview_for_related_person,
    get_related_person,
    list_related_persons,
    validate_related_person_ownership,
)


def related_person_create_data(**overrides):
    data = {
        "first_name": "Anna",
        "last_name": "Kowalska",
        "birth_date": date(2010, 5, 15),
        "guardian_relation": "parent",
        "image_publication_consent": True,
        "vehicle_type": VehicleType.CAR,
        "vehicle_brand": "Toyota",
        "vehicle_model": "Yaris",
        "vehicle_registration_number": "LBI12345",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_related_person(async_session: AsyncSession):
    """Create a related person with valid data."""
    owner_id = uuid4()
    data = RelatedPersonCreate(**related_person_create_data())

    person = await create_related_person(async_session, owner_id, data)
    await async_session.commit()

    assert person.id is not None
    assert person.owner_user_id == owner_id
    assert person.first_name == "Anna"
    assert person.last_name == "Kowalska"
    assert person.birth_date == date(2010, 5, 15)
    assert person.vehicle_brand == "Toyota"


@pytest.mark.asyncio
async def test_create_related_person_without_birth_date(async_session: AsyncSession):
    """Create a related person without optional birth_date."""
    owner_id = uuid4()
    data = RelatedPersonCreate(
        **related_person_create_data(
            first_name="Piotr",
            last_name="Nowak",
            birth_date=None,
        )
    )

    person = await create_related_person(async_session, owner_id, data)
    await async_session.commit()

    assert person.birth_date is None


@pytest.mark.asyncio
async def test_create_related_person_with_false_image_publication_consent(
    async_session: AsyncSession,
):
    """Create a related person with image_publication_consent set to False."""
    owner_id = uuid4()
    data = RelatedPersonCreate(
        **related_person_create_data(
            image_publication_consent=False,
        )
    )

    person = await create_related_person(async_session, owner_id, data)
    await async_session.commit()

    assert person.image_publication_consent is False


@pytest.mark.asyncio
async def test_create_related_person_without_optional_vehicle_details(
    async_session: AsyncSession,
):
    """Create a related person without optional vehicle model and registration."""
    owner_id = uuid4()
    data = RelatedPersonCreate(
        **related_person_create_data(
            vehicle_brand=None,
            vehicle_model=None,
            vehicle_registration_number=None,
        )
    )

    person = await create_related_person(async_session, owner_id, data)
    await async_session.commit()

    assert person.vehicle_type == VehicleType.CAR
    assert person.vehicle_brand is None
    assert person.vehicle_model is None
    assert person.vehicle_registration_number is None


@pytest.mark.asyncio
async def test_get_related_person_success(async_session: AsyncSession):
    """Get a related person with ownership validation."""
    owner_id = uuid4()
    person = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Maria",
        last_name="Lewandowska",
        birth_date=date(2009, 3, 20),
    )
    async_session.add(person)
    await async_session.flush()

    fetched = await get_related_person(async_session, owner_id, person.id)

    assert fetched.id == person.id
    assert fetched.owner_user_id == owner_id


@pytest.mark.asyncio
async def test_get_related_person_not_found(async_session: AsyncSession):
    """Get non-existent related person raises RelatedPersonNotFound."""
    owner_id = uuid4()
    fake_id = uuid4()

    with pytest.raises(RelatedPersonNotFound):
        await get_related_person(async_session, owner_id, fake_id)


@pytest.mark.asyncio
async def test_get_related_person_not_owned_by_user(async_session: AsyncSession):
    """Get related person belonging to another user raises RelatedPersonNotOwnedByUser."""
    owner_id = uuid4()
    other_user_id = uuid4()

    person = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Tomasz",
        last_name="Szymański",
        birth_date=date(2010, 7, 10),
    )
    async_session.add(person)
    await async_session.flush()

    with pytest.raises(RelatedPersonNotOwnedByUser):
        await get_related_person(async_session, other_user_id, person.id)


@pytest.mark.asyncio
async def test_list_related_persons_empty(async_session: AsyncSession):
    """List related persons when none exist."""
    owner_id = uuid4()

    persons = await list_related_persons(async_session, owner_id)

    assert persons == []


@pytest.mark.asyncio
async def test_list_related_persons_multiple(async_session: AsyncSession):
    """List multiple related persons for a guardian."""
    owner_id = uuid4()

    person1 = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Anna",
        last_name="Kowalska",
        birth_date=date(2010, 5, 15),
    )
    person2 = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Piotr",
        last_name="Kowalski",
        birth_date=date(2012, 8, 22),
    )
    async_session.add_all([person1, person2])
    await async_session.flush()

    persons = await list_related_persons(async_session, owner_id)

    assert len(persons) == 2
    assert all(isinstance(p, RelatedPersonWithPreview) for p in persons)


@pytest.mark.asyncio
async def test_list_related_persons_excludes_other_users(async_session: AsyncSession):
    """List only returns related persons for the specified owner."""
    owner_id = uuid4()
    other_user_id = uuid4()

    person1 = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Anna",
        last_name="Kowalska",
    )
    person2 = RelatedPerson(
        owner_user_id=other_user_id,
        first_name="Piotr",
        last_name="Kowalski",
    )
    async_session.add_all([person1, person2])
    await async_session.flush()

    persons = await list_related_persons(async_session, owner_id)

    assert len(persons) == 1
    assert persons[0].first_name == "Anna"


@pytest.mark.asyncio
async def test_list_related_persons_includes_form_preview(
    async_session: AsyncSession,
    active_form,
):
    """List includes last_form_preview for related persons."""
    owner_id = uuid4()
    person = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Anna",
        last_name="Kowalska",
    )
    async_session.add(person)
    await async_session.flush()

    submission = Submission(
        form_id=active_form.id,
        form_version=active_form.version,
        user_id=owner_id,
        filled_for_related_person_id=person.id,
        mode=SubmissionMode.ACCOUNT,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=1,
        sequence_date=date.today(),
        payload_json={"name": "test"},
        consents_json={"rodo": True},
        declarations_accepted=True,
        signed_at=datetime.now(),
    )
    async_session.add(submission)
    await async_session.flush()

    persons = await list_related_persons(async_session, owner_id)

    assert len(persons) == 1
    assert persons[0].last_form_preview is not None
    assert persons[0].last_form_preview.submission_id == submission.id
    assert persons[0].last_form_preview.start_number == 1


@pytest.mark.asyncio
async def test_get_form_preview_none_when_no_submissions(
    async_session: AsyncSession,
):
    """Form preview is None when related person has no submissions."""
    related_person_id = uuid4()

    preview = await get_form_preview_for_related_person(
        async_session,
        related_person_id,
    )

    assert preview is None


@pytest.mark.asyncio
async def test_get_form_preview_returns_latest_submission(
    async_session: AsyncSession,
    active_form,
):
    """Form preview returns the latest submission for related person."""
    owner_id = uuid4()
    person = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Anna",
        last_name="Kowalska",
    )
    async_session.add(person)
    await async_session.flush()

    sub1 = Submission(
        form_id=active_form.id,
        form_version=active_form.version,
        user_id=owner_id,
        filled_for_related_person_id=person.id,
        mode=SubmissionMode.ACCOUNT,
        participant_role=ParticipantRole.DRIVER,
        vehicle_type=VehicleType.CAR,
        start_number=1,
        sequence_date=date.today(),
        payload_json={},
        consents_json={},
        declarations_accepted=True,
        signed_at=datetime.now(),
    )
    sub2 = Submission(
        form_id=active_form.id,
        form_version=active_form.version,
        user_id=owner_id,
        filled_for_related_person_id=person.id,
        mode=SubmissionMode.ACCOUNT,
        participant_role=ParticipantRole.PASSENGER,
        vehicle_type=VehicleType.MOTORCYCLE,
        start_number=2,
        sequence_date=date.today(),
        payload_json={},
        consents_json={},
        declarations_accepted=True,
        signed_at=datetime.now(),
    )
    async_session.add_all([sub1, sub2])
    await async_session.flush()

    preview = await get_form_preview_for_related_person(
        async_session,
        person.id,
    )

    assert preview is not None
    assert preview.start_number == 2
    assert preview.participant_role == ParticipantRole.PASSENGER


@pytest.mark.asyncio
async def test_validate_related_person_ownership_true(
    async_session: AsyncSession,
):
    """Ownership validation returns True when person belongs to user."""
    owner_id = uuid4()
    person = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Anna",
        last_name="Kowalska",
    )
    async_session.add(person)
    await async_session.flush()

    is_owned = await validate_related_person_ownership(
        async_session,
        owner_id,
        person.id,
    )

    assert is_owned is True


@pytest.mark.asyncio
async def test_validate_related_person_ownership_false(
    async_session: AsyncSession,
):
    """Ownership validation returns False for non-existent or non-owned person."""
    owner_id = uuid4()
    other_user_id = uuid4()
    fake_id = uuid4()

    person = RelatedPerson(
        owner_user_id=owner_id,
        first_name="Anna",
        last_name="Kowalska",
    )
    async_session.add(person)
    await async_session.flush()

    is_owned_fake = await validate_related_person_ownership(
        async_session,
        owner_id,
        fake_id,
    )

    is_owned_other = await validate_related_person_ownership(
        async_session,
        other_user_id,
        person.id,
    )

    assert is_owned_fake is False
    assert is_owned_other is False


@pytest.mark.asyncio
async def test_birth_date_validation_future_date():
    """Birth date validation rejects future dates."""
    from datetime import timedelta

    future_date = date.today() + timedelta(days=1)

    with pytest.raises(ValueError, match="cannot be in the future"):
        RelatedPersonCreate(
            **related_person_create_data(
                first_name="Test",
                last_name="Person",
                birth_date=future_date,
            )
        )


@pytest.mark.asyncio
async def test_birth_date_validation_accepts_today():
    """Birth date validation accepts today's date."""
    today = date.today()

    person_data = RelatedPersonCreate(
        **related_person_create_data(
            first_name="Test",
            last_name="Person",
            birth_date=today,
        )
    )

    assert person_data.birth_date == today


@pytest.mark.asyncio
async def test_person_name_validation_empty_first_name():
    """Person name validation rejects empty first name."""
    with pytest.raises(ValueError):
        RelatedPersonCreate(
            **related_person_create_data(
                first_name="",
                last_name="Kowalski",
            )
        )


@pytest.mark.asyncio
async def test_person_name_validation_empty_last_name():
    """Person name validation rejects empty last name."""
    with pytest.raises(ValueError):
        RelatedPersonCreate(
            **related_person_create_data(
                first_name="Jan",
                last_name="",
            )
        )
