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
        "required": ["first_name", "last_name", "birth_date"],
        "properties": {
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "birth_date": {"type": "string", "format": "date"},
        },
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
