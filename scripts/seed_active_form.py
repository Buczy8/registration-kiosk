from __future__ import annotations

import asyncio
import selectors
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
            "signature": "signature_23hbqb",
            "text_fields": {
                "text_10mrbf": "{full_name}",
                "text_11nkwn": "{identity_document}",
                "text_13xmxr": "{residence_address}",
                "text_14shkz": "{birth_date}",
                "text_15abtc": "{phone}",
                "text_16ronm": "{email}",
                "text_17qcbm": "{emergency_contact}",
                "text_18zgmn": "{start_number}",
                "text_19leyv": "{vehicle_brand_model}",
                "text_20vxrd": "{vehicle_registration_number}",
                "text_22jhks": "{minor_full_name}",
                "text_21ebqt": "{signature_place}"
            },
            "checkboxes": {
                "participant_role": {
                    "driver": "checkbox_2yvsn",
                    "passenger": "checkbox_7fncr",
                    "legal_guardian": "checkbox_9xbkw"
                },
                "vehicle_type": {
                    "car": "checkbox_1zoop",
                    "motorcycle": "checkbox_4pht",
                    "gokart": "checkbox_6dpjv"
                },
                "guardian_relation": {
                    "parent": "checkbox_26xkwj",
                    "guardian": "checkbox_25dhmn",
                    "authorized_person": "checkbox_24hzar"
                }
            },
            "consents": {
                "image_publication": "checkbox_23ecm"
            }
        }
    },
    "pdf_template_path": "templates/forms/guest-registration-v2.pdf",
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


def _run_async(coro) -> None:
    if sys.platform == "win32":
        asyncio.run(
            coro,
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
        return
    asyncio.run(coro)


def main() -> None:
    _run_async(async_main())


if __name__ == "__main__":
    main()