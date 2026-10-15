"""Draw a line of text with a TrueType or OpenType face."""
from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFont

from app.handwriting.font_engine import FontEngine, _wrap

log = logging.getLogger(__name__)
INK = (29, 29, 31, 255)


def render_face(
    font_path,
    text: str,
    *,
    weight: float | None,
    max_width_px: int,
    max_height_px: int,
    font_size_pt: float,
    dpi: int,
    line_gap_px: int,
) -> Image.Image:
    if font_path is None:
        return _script_fallback(text, max_width_px, max_height_px, font_size_pt, dpi, line_gap_px)
    size = max(10, int(font_size_pt * dpi / 72))
    try:
        face = ImageFont.truetype(str(font_path), size=size)
        if weight is not None and hasattr(face, "set_variation_by_axes"):
            try:
                face.set_variation_by_axes([weight])
            except OSError:
                pass
    except OSError:
        log.warning("Handwriting font could not be opened: %s", font_path)
        return _script_fallback(text, max_width_px, max_height_px, font_size_pt, dpi, line_gap_px)
    lines = _wrap(text or "", face, max(8, max_width_px))
    gap = line_gap_px or max(2, size // 6)
    line_h = size + gap
    height = max(1, min(max_height_px, line_h * max(1, len(lines))))
    image = Image.new("RGBA", (max(1, max_width_px), height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        y = index * line_h
        if y >= height:
            break
        draw.text((0, y), line, fill=INK, font=face)
    return image


def _script_fallback(text, max_width_px, max_height_px, font_size_pt, dpi, line_gap_px) -> Image.Image:
    return FontEngine().render_wrapped(
        text,
        max_width_px=max_width_px,
        max_height_px=max_height_px,
        style_id=None,
        bias=0.75,
        variation=0,
        font_size_pt=font_size_pt,
        dpi=dpi,
        seed=None,
        line_gap_px=line_gap_px,
    )
