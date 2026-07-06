from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.form import Form

ACTIVE_FORM_CODE = "guest-registration"

ACTIVE_FORM_DATA = {
    "code": ACTIVE_FORM_CODE,
    "name": "Rejestracja gościa",
    "version": "1.0",
    "schema_json": {
        "required": [
            "first_name",
            "last_name",
            "residence_address",
            "birth_date",
            "phone",
            "email",
            "emergency_contact_name",
            "emergency_contact_phone",
            "signature_place",
        ],
        "properties": {
            "first_name": {"type": "string", "title": "Imię"},
            "last_name": {"type": "string", "title": "Nazwisko"},
            "pesel": {"type": "string", "title": "PESEL", "pattern": "^[0-9]{11}$"},
            "id_card_series": {"type": "string", "title": "Seria dowodu osobistego"},
            "id_card_number": {"type": "string", "title": "Numer dowodu osobistego"},
            "residence_address": {"type": "string", "title": "Adres zamieszkania"},
            "birth_date": {"type": "string", "format": "date", "title": "Data urodzenia"},
            "phone": {"type": "string", "title": "Telefon"},
            "email": {"type": "string", "format": "email", "title": "E-mail"},
            "emergency_contact_name": {
                "type": "string",
                "title": "Kontakt ICE – imię i nazwisko",
            },
            "emergency_contact_phone": {
                "type": "string",
                "title": "Kontakt ICE – telefon",
            },
            "vehicle_brand": {"type": "string", "title": "Marka pojazdu"},
            "vehicle_model": {"type": "string", "title": "Model pojazdu"},
            "vehicle_registration_number": {
                "type": "string",
                "title": "Numer rejestracyjny",
            },
            "guardian_relation": {"type": "string", "title": "Typ opiekuna"},
            "minor_first_name": {"type": "string", "title": "Imię podopiecznego"},
            "minor_last_name": {"type": "string", "title": "Nazwisko podopiecznego"},
            "signature_place": {"type": "string", "title": "Data i miejscowość"},
        },
        "identity_document_rule": "pesel_or_id_card",
        "pdf_mapping": {
            "signature": {
                "page": 0,
                "rect": [597, 476, 719, 507]
            },
            "text_fields": {
                "text_8fpaj": "{first_name} {last_name}",
                "text_9yvjs": "{pesel}{id_card_series} {id_card_number}",
                "text_10oepk": "{residence_address}",
                "text_11nkcj": "{birth_date}",
                "text_12fueu": "{phone}",
                "text_13ywdm": "{email}",
                "text_14ofnm": "{emergency_contact_name}, {emergency_contact_phone}",
                "text_15qcfa": "{start_number}",
                "text_16ulhc": "{vehicle_brand} {vehicle_model}",
                "text_17bbxm": "{vehicle_registration_number}",
                "text_18lzou": "{minor_first_name} {minor_last_name}",
                "text_24wgja": "{signature_place}"
            },
            "checkboxes": {
                "participant_role": {
                    "driver": "checkbox_26aqhm",
                    "passenger": "checkbox_3klde",
                    "legal_guardian": "checkbox_27ywf"
                },
                "vehicle_type": {
                    "car": "checkbox_29pnyu",
                    "motorcycle": "checkbox_25ahnh",
                    "gokart": "checkbox_30txms"
                },
                "guardian_relation": {
                    "parent": "checkbox_19pppm",
                    "guardian": "checkbox_20jfuy",
                    "authorized_person": "checkbox_21iohl"
                }
            },
            "consents": {
                "privacy": "checkbox_22zynj",
                "image_publication": "checkbox_23dbga"
            }
        }
    },
    "pdf_template_path": "templates/forms/guest-registration-v1.pdf",
    "is_active": True,
}


async def _deactivate_other_active_forms(db: AsyncSession, *, except_code: str) -> None:
    result = await db.execute(
        select(Form).where(Form.is_active.is_(True), Form.code != except_code)
    )
    for form in result.scalars():
        form.is_active = False


async def seed_active_form(db: AsyncSession | None = None) -> Form:
    owns_session = db is None
    db = db or AsyncSessionLocal()
    try:
        await _deactivate_other_active_forms(db, except_code=ACTIVE_FORM_CODE)

        result = await db.execute(
            select(Form).where(Form.code == ACTIVE_FORM_CODE)
        )
        form = result.scalar_one_or_none()

        if form is None:
            form = Form(**ACTIVE_FORM_DATA)
            db.add(form)
        else:
            for key, value in ACTIVE_FORM_DATA.items():
                setattr(form, key, value)

        await db.commit()
        await db.refresh(form)
        return form
    except Exception:
        await db.rollback()
        raise
    finally:
        if owns_session:
            await db.close()


async def async_main() -> None:
    form = await seed_active_form()
    print(
        f"Seeded active form: code={form.code}, id={form.id}, "
        f"version={form.version}, is_active={form.is_active}"
    )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()