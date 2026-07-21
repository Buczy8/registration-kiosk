from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
import fitz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.models.submission import Submission
from app.services.pdf_mapping import (
    PdfFieldMapping,
    get_guest_submission_pdf_mapping,
)
from app.services.signatures import load_submission_signature_bytes

POLISH_FONT_NAME = "LibSans"
POLISH_FONT_BUNDLED = PROJECT_ROOT / "assets" / "fonts" / "LiberationSans-Regular.ttf"
POLISH_FONT_SYSTEM = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
DEFAULT_TEXT_FONT_SIZE = 10.0
MIN_TEXT_FONT_SIZE = 5.0
TEXT_WIDTH_MARGIN_RATIO = 0.98
TEXT_HEIGHT_MARGIN_RATIO = 0.85


def _resolve_template_path(template_path: str) -> Path:
    path = Path(template_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _resolve_polish_font_path() -> Path:
    if POLISH_FONT_BUNDLED.exists():
        return POLISH_FONT_BUNDLED
    if POLISH_FONT_SYSTEM.exists():
        return POLISH_FONT_SYSTEM
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            "Brak fontu obsługującego polskie znaki. "
            f"Oczekiwany plik: {POLISH_FONT_BUNDLED}"
        ),
    )


def _ensure_polish_font(page: fitz.Page, font_path: Path, embedded_pages: set[int]) -> None:
    if page.number in embedded_pages:
        return
    page.insert_font(fontname=POLISH_FONT_NAME, fontfile=str(font_path))
    embedded_pages.add(page.number)


def _load_polish_font(font_path: Path) -> fitz.Font:
    return fitz.Font(fontfile=str(font_path))


def _preferred_fontsize(widget: fitz.Widget) -> float:
    if widget.text_fontsize and widget.text_fontsize > 0:
        return widget.text_fontsize
    return DEFAULT_TEXT_FONT_SIZE


def _max_fontsize_for_height(font: fitz.Font, rect: fitz.Rect) -> float:
    line_height = font.ascender + abs(font.descender)
    if line_height <= 0:
        return DEFAULT_TEXT_FONT_SIZE
    return (rect.height * TEXT_HEIGHT_MARGIN_RATIO) / line_height


def _fit_fontsize(font: fitz.Font, text: str, rect: fitz.Rect, preferred: float) -> float:
    start_size = min(preferred, _max_fontsize_for_height(font, rect))
    fontsize = start_size
    max_width = rect.width * TEXT_WIDTH_MARGIN_RATIO

    while fontsize >= MIN_TEXT_FONT_SIZE:
        if font.text_length(text, fontsize=fontsize) <= max_width:
            line_height = fontsize * (font.ascender + abs(font.descender))
            if line_height <= rect.height * TEXT_HEIGHT_MARGIN_RATIO:
                return fontsize
        fontsize -= 0.5

    return MIN_TEXT_FONT_SIZE


def _baseline_y(rect: fitz.Rect, font: fitz.Font, fontsize: float) -> float:
    ascender = font.ascender * fontsize
    descender = abs(font.descender * fontsize)
    return rect.y0 + (rect.height + ascender + descender) / 2 - descender


def _flatten_text_widget(page: fitz.Page, widget: fitz.Widget, value: str, font: fitz.Font) -> None:
    rect = widget.rect
    if value:
        fontsize = _fit_fontsize(font, value, rect, _preferred_fontsize(widget))
        baseline_y = _baseline_y(rect, font, fontsize)
        page.insert_text(
            (rect.x0, baseline_y),
            value,
            fontname=POLISH_FONT_NAME,
            fontsize=fontsize,
        )
    page.delete_widget(widget)


def _write_pdf_fields(doc: fitz.Document, mapping: PdfFieldMapping) -> None:
    font_path = _resolve_polish_font_path()
    embedded_pages: set[int] = set()
    polish_font = _load_polish_font(font_path)

    for page in doc:
        text_widgets: list[tuple[fitz.Widget, str]] = []

        for widget in page.widgets() or []:
            if widget.field_name in mapping.text_values:
                text_widgets.append((widget, mapping.text_values[widget.field_name]))
            elif widget.field_name in mapping.managed_checkboxes:
                if widget.field_name in mapping.checked_fields:
                    widget.field_value = widget.on_state() or "Yes"
                else:
                    widget.field_value = ""
                widget.update()

        if not text_widgets:
            continue

        _ensure_polish_font(page, font_path, embedded_pages)
        for widget, value in text_widgets:
            _flatten_text_widget(page, widget, value, polish_font)










def _embed_signature_image(
        doc: fitz.Document,
        submission: Submission,
        settings: Settings | None,
        mapping: PdfFieldMapping,
) -> None:
    if settings is None or not submission.signature_path:
        return

    sig_page = None
    sig_rect = None

    # 1. Try to find the signature widget by its mapped field name
    if mapping.signature_field_name:
        for page_idx, page in enumerate(doc):
            for widget in page.widgets() or []:
                if widget.field_name == mapping.signature_field_name:
                    sig_page = page_idx
                    sig_rect = widget.rect
                    break
            if sig_rect is not None:
                break

    # 2. Fallback to coordinates defined in the mapping
    if sig_page is None or sig_rect is None:
        sig_page = mapping.signature_page
        sig_rect = mapping.signature_rect

    # 3. Fallback to generic auto-detection by name match
    if sig_page is None or sig_rect is None:
        for page_idx, page in enumerate(doc):
            for widget in page.widgets() or []:
                if widget.field_name and (
                    widget.field_name.startswith("signature")
                    or "signature" in widget.field_name.lower()
                ):
                    sig_page = page_idx
                    sig_rect = widget.rect
                    break
            if sig_rect is not None:
                break

    if sig_page is None or sig_rect is None:
        return

    image_bytes = load_submission_signature_bytes(settings, submission.signature_path)
    if not image_bytes:
        return

    if sig_page >= len(doc):
        return

    page = doc[sig_page]
    for widget in list(page.widgets() or []):
        if widget.field_name == mapping.signature_field_name or (
            widget.field_name and "signature" in widget.field_name.lower()
        ):
            page.delete_widget(widget)
    page.insert_image(sig_rect, stream=image_bytes, keep_proportion=True, rotate=page.rotation)




def fill_guest_submission_template(submission: Submission, *, settings: Settings | None = None) -> bytes:
    if submission.form is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission form not loaded")

    template_path = _resolve_template_path(submission.form.pdf_template_path)
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF template not found: {template_path}",
        )

    mapping = get_guest_submission_pdf_mapping(submission)

    with fitz.open(template_path) as doc:
        if hasattr(doc, "need_appearances"):
            doc.need_appearances(True)

        _write_pdf_fields(doc, mapping)
        _embed_signature_image(doc, submission, settings, mapping)
        return doc.write(garbage=4, deflate=True)


async def generate_submission_pdf(db: AsyncSession, submission_id: UUID) -> tuple[Submission, bytes]:
    stmt = (
        select(Submission)
        .options(selectinload(Submission.form))
        .where(Submission.id == submission_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()

    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    settings = get_settings()
    pdf_bytes = await asyncio.to_thread(
        fill_guest_submission_template, submission, settings=settings
    )
    submission.pdf_path = f"generated://submissions/{submission.id}.pdf"

    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission, pdf_bytes


def render_pdf_to_png(pdf_bytes: bytes, page_index: int = 0, dpi: int = 150) -> bytes:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if page_index < 0 or page_index >= len(doc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strona {page_index} nie istnieje w dokumencie PDF (liczba stron: {len(doc)}).",
            )
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        png_data = pix.tobytes("png")

        # Zapisz kopie roboczą do szybkiego podglądu i weryfikacji
        debug_path = PROJECT_ROOT / "scratch" / "debug_last_png.png"
        debug_path.write_bytes(png_data)

        return png_data








async def generate_submission_png(
    db: AsyncSession, submission_id: UUID, page_index: int = 0, dpi: int = 150
) -> tuple[Submission, bytes]:
    submission, pdf_bytes = await generate_submission_pdf(db=db, submission_id=submission_id)
    png_bytes = await asyncio.to_thread(render_pdf_to_png, pdf_bytes, page_index, dpi)
    return submission, png_bytes

