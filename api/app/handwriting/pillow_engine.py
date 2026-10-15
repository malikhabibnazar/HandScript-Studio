"""Adult handwriting faces drawn with Pillow. No GPU and no extra tools."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.handwriting.ttf_draw import render_face

FONTS = Path(__file__).resolve().parent / "fonts"

# id, label, file, variable-font weight or None
FACES: dict[str, tuple[str, str, float | None]] = {
    "caveat": ("Caveat", "Caveat-Variable.ttf", 560),
    "homemade": ("Homemade Apple", "HomemadeApple-Regular.ttf", None),
    "patrick": ("Patrick Hand", "PatrickHand-Regular.ttf", None),
    "kalam": ("Kalam", "Kalam-Regular.ttf", None),
    "sacramento": ("Sacramento", "Sacramento-Regular.ttf", None),
    "architects": ("Architects Daughter", "ArchitectsDaughter-Regular.ttf", None),
}


def face_catalog() -> list[dict]:
    rows = []
    for key, (label, filename, _weight) in FACES.items():
        rows.append({"id": key, "label": label, "installed": (FONTS / filename).is_file()})
    return rows


def resolve_face(family: str | None) -> tuple[str, Path | None, float | None]:
    key = (family or "caveat").strip().lower()
    if key not in FACES:
        key = "caveat"
    label, filename, weight = FACES[key]
    path = FONTS / filename
    return label, path if path.is_file() else None, weight


class PillowEngine:
    name = "pillow"

    def __init__(self, family: str | None = None) -> None:
        self.family, self.font_path, self.weight = resolve_face(family)

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
