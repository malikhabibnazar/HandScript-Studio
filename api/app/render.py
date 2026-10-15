"""Render one document page to PDF or PNG at the template's physical size.

Text, address and data-field blocks are drawn by the profile's handwriting
engine (Graves, Handwrite, or the script-font fallback). PDF and PNG use the same pixels.
The PDF page box stays in real inches.
"""
from __future__ import annotations

import hashlib
import io
from contextlib import nullcontext

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from app.handwriting.factory import get_handwriting_engine

INK = (29, 29, 31, 255)


def fill_text(content: str, record: dict) -> str:
    text = content or ""
    for key, value in record.items():
        if str(key).startswith("_"):
            continue
        text = text.replace("{" + str(key) + "}", "" if value is None else str(value))
    return text


def stable_seed(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def parse_dpi(resolution: str | None) -> int:
    digits = "".join(ch if ch.isdigit() else " " for ch in (resolution or "300 dpi")).split()
    value = int(digits[0]) if digits else 300
    return min(600, max(72, value))


def render_page(
    template: dict,
    elements: list[dict],
    record: dict,
    *,
    dpi: int = 300,
    seed: int = 0,
    style_id: int | None = None,
    bias: float = 0.75,
    variation: float = 0.15,
    engine: str | None = None,
    font_path: str | None = None,
    font_family: str | None = None,
    sample_keys: list[str] | None = None,
) -> Image.Image:
    width = max(1, int(round(float(template["width_in"]) * dpi)))
    height = max(1, int(round(float(template["height_in"]) * dpi)))
    page = Image.new("RGB", (width, height), "white")
    writer = get_handwriting_engine(engine, font_path=font_path, font_family=font_family)
    sample_ctx = nullcontext()
    engine_norm = (engine or "").strip().lower()
    if engine_norm in {"gemini", "onedm"}:
        if engine_norm == "gemini":
            from app.handwriting.gemini_engine import use_samples
        else:
            from app.handwriting.onedm_engine import use_samples
        from app.storage import get_storage

        blobs: list[bytes] = []
        store = get_storage()
        for key in sample_keys or []:
            try:
                blobs.append(store.get(key))
            except Exception:
                continue
        sample_ctx = use_samples(blobs)
    with sample_ctx:
        _draw_elements(page, writer, elements, record, dpi=dpi, seed=seed, width=width, height=height, style_id=style_id, bias=bias, variation=variation)
    return page


def _draw_elements(page, writer, elements, record, *, dpi, seed, width, height, style_id, bias, variation) -> None:
    for index, element in enumerate(elements):
        if not element.get("visible", True):
            continue
        box = _box(element, dpi, width, height)
        if element.get("type") == "Divider":
            _divider(page, box, dpi)
            continue
        if element.get("type") == "Image":
            continue
        text = fill_text(element.get("content") or "", record)
        if not text.strip():
            continue
        ink = writer.render_wrapped(
            text,
            max_width_px=box[2],
            max_height_px=box[3],
            style_id=style_id,
            bias=bias,
            variation=variation,
            font_size_pt=float(element.get("font_size") or 14),
            dpi=dpi,
            seed=stable_seed(seed, index, text),
            line_gap_px=max(2, int(float(element.get("font_size") or 14) * dpi / 72 * 0.25)),
        )
        _paste(page, ink, box)


def render_png(template: dict, elements: list[dict], record: dict, dpi: int = 150, **ink) -> bytes:
    image = render_page(template, elements, record, dpi=dpi, **ink)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def render_pdf(template: dict, elements: list[dict], record: dict, dpi: int = 300, **ink) -> bytes:
    return _pdf_from_pages([render_page(template, elements, record, dpi=dpi, **ink)], template)


def render_combined_pdf(
    template: dict,
    elements: list[dict],
    records: list[dict],
    *,
    dpi: int = 300,
    seeds: list[int] | None = None,
    **ink,
) -> bytes:
    pages = []
    for index, record in enumerate(records or [{}]):
        seed = seeds[index] if seeds and index < len(seeds) else index
        pages.append(render_page(template, elements, record, dpi=dpi, seed=seed, **ink))
    return _pdf_from_pages(pages, template)


def _box(element: dict, dpi: int, page_w: int, page_h: int) -> tuple[int, int, int, int]:
    x = int(round(float(element.get("x") or 0) * dpi))
    y = int(round(float(element.get("y") or 0) * dpi))
    w = max(1, int(round(float(element.get("width") or 0.1) * dpi)))
    h = max(1, int(round(float(element.get("height") or 0.1) * dpi)))
    x = min(max(0, x), page_w - 1)
    y = min(max(0, y), page_h - 1)
    w = min(w, page_w - x)
    h = min(h, page_h - y)
    return x, y, max(1, w), max(1, h)


def _paste(page: Image.Image, ink: Image.Image, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    fitted = ink.convert("RGBA")
    if fitted.width > w or fitted.height > h:
        fitted.thumbnail((w, h), Image.Resampling.LANCZOS)
    page.paste(fitted, (x, y), fitted)


def _divider(page: Image.Image, box: tuple[int, int, int, int], dpi: int) -> None:
    from PIL import ImageDraw

    x, y, w, h = box
    draw = ImageDraw.Draw(page)
    mid = y + h // 2
    draw.line((x, mid, x + w, mid), fill=(197, 200, 206), width=max(1, dpi // 200))


def _pdf_from_pages(pages: list[Image.Image], template: dict) -> bytes:
    width = float(template["width_in"]) * 72
    height = float(template["height_in"]) * 72
    buf = io.BytesIO()
    pdf = pdfcanvas.Canvas(buf, pagesize=(width, height))
    for index, page in enumerate(pages):
        stream = io.BytesIO()
        page.save(stream, format="PNG")
        stream.seek(0)
        pdf.drawImage(ImageReader(stream), 0, 0, width=width, height=height, preserveAspectRatio=False, mask="auto")
        if index < len(pages) - 1:
            pdf.showPage()
    pdf.save()
    return buf.getvalue()
