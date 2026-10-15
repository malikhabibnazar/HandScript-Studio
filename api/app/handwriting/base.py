"""The renderer talks to this protocol and nothing Graves-specific."""
from __future__ import annotations

from typing import Protocol

from PIL import Image


class HandwritingEngine(Protocol):
    name: str

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
    ) -> Image.Image: ...

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
    ) -> Image.Image: ...
