from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
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
    },
    "pdf_template_path": "templates/forms/guest-registration-v1.pdf",
    "is_active": True,
}


def _deactivate_other_active_forms(db: Session, *, except_code: str) -> None:
    for form in db.execute(
        select(Form).where(Form.is_active.is_(True), Form.code != except_code)
    ).scalars():
        form.is_active = False


def seed_active_form(db: Session | None = None) -> Form:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        _deactivate_other_active_forms(db, except_code=ACTIVE_FORM_CODE)

        form = db.execute(
            select(Form).where(Form.code == ACTIVE_FORM_CODE)
        ).scalar_one_or_none()

        if form is None:
            form = Form(**ACTIVE_FORM_DATA)
            db.add(form)
        else:
            for key, value in ACTIVE_FORM_DATA.items():
                setattr(form, key, value)

        db.commit()
        db.refresh(form)
        return form
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()


def main() -> None:
    form = seed_active_form()
    print(
        f"Seeded active form: code={form.code}, id={form.id}, "
        f"version={form.version}, is_active={form.is_active}"
    )


if __name__ == "__main__":
    main()
