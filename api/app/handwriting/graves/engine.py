"""Adapt the Graves sampler to the handwriting engine protocol."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.handwriting.graves.model import GravesModel, Weights


def _chunks(text: str, budget: int) -> list[str]:
    lines: list[str] = []
    for paragraph in (text or "").split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            pieces = [word[i:i + budget] for i in range(0, max(len(word), 1), budget)] if word else [""]
            for piece in pieces:
                trial = piece if not current else f"{current} {piece}"
                if len(trial) <= budget or not current:
                    current = trial
                else:
                    lines.append(current)
                    current = piece
        lines.append(current)
    return [line for line in lines if line] or [""]


class GravesEngine:
    name = "graves"

    def __init__(self, weights_path: Path, styles_dir: Path) -> None:
        self.model = GravesModel(Weights.load(weights_path), styles_dir)
        self.weights_path = weights_path

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
        stroke = max(1, int(font_size_pt * dpi / 72 * 0.07))
        image = self.model.render_image(
            text,
            style_id=style_id,
            bias=bias,
            variation=variation,
            seed=seed,
            max_width_px=max(2, max_width_px),
            max_height_px=max(2, max_height_px),
            stroke_px=stroke,
        )
        if image.width > max_width_px or image.height > max_height_px:
            image.thumbnail((max(1, max_width_px), max(1, max_height_px)), Image.Resampling.LANCZOS)
        return image

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
        px_per_char = max(8.0, font_size_pt * dpi / 72 * 0.5)
        budget = max(8, min(70, int(max_width_px / px_per_char)))
        lines = _chunks(text, budget)
        gap = line_gap_px or max(4, int(font_size_pt * dpi / 72 * 0.35))
        rendered = []
        for index, line in enumerate(lines):
            line_seed = None if seed is None else (seed + index * 997) & 0xFFFFFFFF
            rendered.append(self.render_line(
                line,
                style_id=style_id,
                bias=bias,
                variation=variation,
                font_size_pt=font_size_pt,
                dpi=dpi,
                seed=line_seed,
                max_width_px=max_width_px,
                max_height_px=max_height_px,
            ))
        width = min(max_width_px, max(image.width for image in rendered))
        height = sum(image.height for image in rendered) + gap * (len(rendered) - 1)
        canvas = Image.new("RGBA", (max(1, width), max(1, height)), (0, 0, 0, 0))
        y = 0
        for image in rendered:
            canvas.alpha_composite(image, (0, y))
            y += image.height + gap
        if canvas.width > max_width_px or canvas.height > max_height_px:
            canvas.thumbnail((max(1, max_width_px), max(1, max_height_px)), Image.Resampling.LANCZOS)
        return canvas
