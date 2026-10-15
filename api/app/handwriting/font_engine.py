"""Script-font fallback. Same pixel path as Graves, so PDF and PNG match."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.handwriting.base import HandwritingEngine


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        r"C:\Windows\Fonts\segoesc.ttf",
        r"C:\Windows\Fonts\comic.ttf",
        r"C:\Windows\Fonts\BRADHITC.TTF",
        "/System/Library/Fonts/Supplemental/SnellRoundhand.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size=max(8, size))
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        if not words:
            lines.append("")
            continue
        current = ""
        pieces: list[str] = []
        for word in words:
            if font.getlength(word) <= max_width:
                pieces.append(word)
                continue
            token = ""
            for char in word:
                trial = token + char
                if font.getlength(trial) <= max_width or not token:
                    token = trial
                else:
                    pieces.append(token)
                    token = char
            if token:
                pieces.append(token)
        for word in pieces:
            trial = word if not current else f"{current} {word}"
            if font.getlength(trial) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines or [""]


class FontEngine:
    name = "font"

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
        del style_id, bias, variation, seed
        return self.render_wrapped(
            text,
            max_width_px=max_width_px,
            max_height_px=max_height_px,
            style_id=None,
            bias=0.0,
            variation=0.0,
            font_size_pt=font_size_pt,
            dpi=dpi,
            seed=None,
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
        size = max(10, int(font_size_pt * dpi / 72))
        face = _font(size)
        lines = _wrap(text or "", face, max(8, max_width_px))
        gap = line_gap_px or max(2, size // 5)
        line_h = size + gap
        height = max(1, min(max_height_px, line_h * max(1, len(lines))))
        image = Image.new("RGBA", (max(1, max_width_px), height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(lines):
            y = index * line_h
            if y >= height:
                break
            draw.text((0, y), line, fill=(29, 29, 31, 255), font=face)
        return image


def as_engine() -> HandwritingEngine:
    return FontEngine()
