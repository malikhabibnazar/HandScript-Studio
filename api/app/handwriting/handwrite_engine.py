"""Handwrite renderer.

The PyPI `handwrite` package turns a filled sample sheet into a TTF. That
conversion needs Potrace and FontForge. Cards still have to print when those
tools are absent, so this engine draws with a bundled handwriting face and
switches to a converted profile font when one exists.
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.handwriting.font_engine import FontEngine, _wrap

log = logging.getLogger(__name__)

BUNDLED_FONT = Path(__file__).resolve().parent / "fonts" / "PatrickHand-Regular.ttf"
INK = (29, 29, 31, 255)


def handwrite_status() -> dict:
    version = None
    package = False
    try:
        import importlib.metadata

        version = importlib.metadata.version("handwrite")
        package = True
    except Exception:
        package = False
    potrace = shutil.which("potrace") is not None
    fontforge = bool(shutil.which("ffpython") or shutil.which("fontforge"))
    return {
        "package": package,
        "version": version,
        "potrace": potrace,
        "fontforge": fontforge,
        "personal_font": package and potrace and fontforge,
        "bundled_font": BUNDLED_FONT.exists(),
    }


def convert_sample_sheet(sheet: bytes, dest_ttf: Path) -> str | None:
    """Build a TTF with the handwrite package. Returns an error, or None."""
    status = handwrite_status()
    if not status["package"]:
        return "The handwrite package is not installed."
    if not status["potrace"] or not status["fontforge"]:
        return "Potrace and FontForge are required to turn a sample sheet into a font."
    try:
        from handwrite import converters
    except Exception as exc:
        return f"handwrite could not be imported ({exc})."
    dest_ttf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handwrite-") as temp:
        root = Path(temp)
        sheet_path = root / "sheet.png"
        sheet_path.write_bytes(sheet)
        out = root / "out"
        out.mkdir()
        try:
            converters(str(sheet_path), str(out))
        except Exception as exc:
            log.warning("handwrite conversion failed: %s", exc)
            return f"Sample sheet was not converted ({exc})."
        found = sorted(out.rglob("*.ttf"))
        if not found:
            return "handwrite finished without a font file."
        dest_ttf.write_bytes(found[0].read_bytes())
    return None


def attach_personal_font(profile_id: str, samples: list, style: dict, read_sample) -> dict:
    """Keep a converted font on the profile when the chosen sheet tool can build one."""
    stored = dict(style or {})
    engine = str(stored.get("engine") or "").lower()
    if engine not in {"handwrite", "hw2font", "fontmaker"}:
        return stored
    if not samples:
        return stored
    if engine == "handwrite" and not handwrite_status()["personal_font"]:
        return stored
    if engine in {"hw2font", "fontmaker"}:
        from app.handwriting.sheet_engine import sheet_status

        if not sheet_status()["personal_font"]:
            return stored
    sample = samples[-1]
    key = f"samples/{profile_id}/{sample.get('id')}-{sample.get('filename')}"
    try:
        raw = read_sample(key)
    except Exception as exc:
        log.info("Sample %s could not be read for handwrite: %s", key, exc)
        return stored
    from app.config import get_settings

    suffix = ".otf" if engine == "hw2font" else ".ttf"
    dest = Path(get_settings().storage_dir) / "handwrite" / f"{profile_id}-{engine}{suffix}"
    if engine == "handwrite":
        error = convert_sample_sheet(raw, dest)
    else:
        from app.handwriting.sheet_engine import convert_sheet

        error = convert_sheet(engine, raw, dest)
    if error:
        log.info("Profile %s is using the built-in handwrite face: %s", profile_id, error)
        return stored
    stored["font_path"] = str(dest)
    return stored


def _pick_font(font_path: str | None) -> Path | None:
    if font_path:
        candidate = Path(font_path)
        if candidate.is_file():
            return candidate
    if BUNDLED_FONT.is_file():
        return BUNDLED_FONT
    return None


class HandwriteEngine:
    name = "handwrite"

    def __init__(self, font_path: str | None = None) -> None:
        self.font_path = _pick_font(font_path)

    def render_line(
        self,
        text: str,
        *,
        style_id: int | None,
        bias: float,
        variation: float,
        font_size_pt: float,
        dpi: int,
        seed: int | None,
        max_width_px: int,
        max_height_px: int,
    ) -> Image.Image:
        return self.render_wrapped(
            text,
            max_width_px=max_width_px,
            max_height_px=max_height_px,
            style_id=style_id,
            bias=bias,
            variation=variation,
            font_size_pt=font_size_pt,
            dpi=dpi,
            seed=seed,
            line_gap_px=0,
        )

    def render_wrapped(
        self,
        text: str,
        *,
        max_width_px: int,
        max_height_px: int,
        style_id: int | None,
        bias: float,
        variation: float,
        font_size_pt: float,
        dpi: int,
        seed: int | None,
        line_gap_px: int,
    ) -> Image.Image:
        del style_id, bias, variation, seed
        if self.font_path is None:
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
        size = max(10, int(font_size_pt * dpi / 72))
        try:
            face = ImageFont.truetype(str(self.font_path), size=size)
        except OSError:
            log.warning("Handwrite font could not be opened: %s", self.font_path)
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
