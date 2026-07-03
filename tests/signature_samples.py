import base64

import fitz


def sample_signature_png() -> bytes:
    document = fitz.open()
    page = document.new_page(width=300, height=120)
    page.draw_line((20, 60), (280, 60), color=(0, 0, 0), width=2)
    page.draw_line((150, 20), (200, 100), color=(0, 0, 0), width=2)
    pixmap = page.get_pixmap()
    return pixmap.tobytes("png")


def sample_signature_base64() -> str:
    return base64.b64encode(sample_signature_png()).decode("ascii")
