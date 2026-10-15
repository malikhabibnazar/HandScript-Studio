"""hw2font and handwrite-font-maker.

Both turn a filled specimen sheet into a font. That step needs Potrace and
FontForge. Until a sheet converts, cards use a distinct built-in handwriting
face so a batch still prints.
"""
from __future__ import annotations

import logging
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

from app.handwriting.pillow_engine import PillowEngine
from app.handwriting.ttf_draw import render_face

log = logging.getLogger(__name__)

THIRD_PARTY = Path(__file__).resolve().parents[2] / "third_party"
FALLBACK = {"hw2font": "homemade", "fontmaker": "sacramento"}


def _vendor_path() -> None:
    root = str(THIRD_PARTY)
    if root not in sys.path:
        sys.path.insert(0, root)


def _tools() -> dict:
    potrace = shutil.which("potrace") is not None
    fontforge = bool(shutil.which("ffpython") or shutil.which("fontforge"))
    return {"potrace": potrace, "fontforge": fontforge, "ready": potrace and fontforge}


def _importable(module: str) -> bool:
    _vendor_path()
    try:
        __import__(module)
    except Exception as exc:
        log.info("%s is not importable: %s", module, exc)
        return False
    return True


def sheet_status() -> dict:
    tools = _tools()
    hw2font = _importable("hw2font.template.generator") and _importable("hw2font.extract.pipeline")
    fontmaker = _importable("handwrite_font_maker.pipeline") and _importable("handwrite_font_maker.template")
    return {
        "potrace": tools["potrace"],
        "fontforge": tools["fontforge"],
        "hw2font": hw2font,
        "fontmaker": fontmaker,
        "personal_font": tools["ready"],
    }


class SheetEngine:
    def __init__(self, name: str, font_path: str | None = None) -> None:
        self.name = name
        personal = Path(font_path) if font_path else None
        if personal is not None and personal.is_file():
            self.font_path = personal
            self.weight = None
            self.personal = True
        else:
            face = PillowEngine(FALLBACK.get(name, "homemade"))
            self.font_path = face.font_path
            self.weight = face.weight
            self.personal = False

    def render_line(self, text: str, *, style_id, bias, variation, font_size_pt, dpi, seed, max_width_px, max_height_px) -> Image.Image:
        return self.render_wrapped(
            text, max_width_px=max_width_px, max_height_px=max_height_px, style_id=style_id,
            bias=bias, variation=variation, font_size_pt=font_size_pt, dpi=dpi, seed=seed, line_gap_px=0,
        )

    def render_wrapped(self, text: str, *, max_width_px, max_height_px, style_id, bias, variation, font_size_pt, dpi, seed, line_gap_px) -> Image.Image:
        del style_id, bias, variation, seed
        return render_face(
            self.font_path, text, weight=self.weight, max_width_px=max_width_px, max_height_px=max_height_px,
            font_size_pt=font_size_pt, dpi=dpi, line_gap_px=line_gap_px,
        )


def template_pdf(kind: str) -> bytes:
    _vendor_path()
    with tempfile.TemporaryDirectory(prefix="sheet-template-") as temp:
        dest = Path(temp) / "template.pdf"
        if kind == "hw2font":
            from hw2font.template.generator import generate_template

            generate_template(dest)
        elif kind == "fontmaker":
            from handwrite_font_maker.template import generate_template_pdf

            generate_template_pdf(dest, include_markers=True)
        else:
            raise ValueError(kind)
        return dest.read_bytes()


def convert_sheet(kind: str, sheet: bytes, dest: Path) -> str | None:
    """Build a personal font. Returns an error string, or None on success."""
    tools = _tools()
    if not tools["ready"]:
        return "Potrace and FontForge are required to turn a sample sheet into a font."
    _vendor_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{kind}-") as temp:
        root = Path(temp)
        image = root / "sheet.png"
        image.write_bytes(sheet)
        try:
            if kind == "hw2font":
                from hw2font.compile.builder import compile_font
                from hw2font.extract.pipeline import extract_glyphs

                extracted, _stats = extract_glyphs([image], root / "extracted", dpi=300)
                built = compile_font(extracted, dest, dpi=300, font_name="ProfileHand")
                if Path(built) != dest and Path(built).is_file():
                    dest.write_bytes(Path(built).read_bytes())
            elif kind == "fontmaker":
                from handwrite_font_maker.pipeline import build_font

                outputs = build_font(
                    image_path=image,
                    font_name="ProfileHand",
                    family_name="Profile Hand",
                    style_name="Regular",
                    output_dir=root / "out",
                    alignment="markers",
                )
                source = Path(str(outputs.get("ttf") or outputs.get("otf") or ""))
                if not source.is_file():
                    return "Font maker finished without a font file."
                dest.write_bytes(source.read_bytes())
            else:
                return f"Unknown sheet renderer {kind}."
        except Exception as exc:
            log.warning("%s conversion failed: %s", kind, exc)
            return f"Sample sheet was not converted ({exc})."
    if not dest.is_file() or dest.stat().st_size < 64:
        return "Sample sheet was not converted."
    return None
