"""Rasterise Graves pen offsets into an ink image that fits a box."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw


def offsets_to_coords(offsets: np.ndarray) -> np.ndarray:
    coords = np.cumsum(offsets[:, :2], axis=0)
    coords[:, 1] *= -1
    eos = offsets[:, 2:3]
    return np.concatenate([coords, eos], axis=1)


def draw_strokes(
    offsets: np.ndarray,
    *,
    max_width_px: int,
    max_height_px: int,
    stroke_px: int,
) -> Image.Image:
    if offsets.size == 0 or max_width_px < 2 or max_height_px < 2:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    coords = offsets_to_coords(np.asarray(offsets, dtype=np.float32))
    xy = coords[:, :2]
    span = xy.max(axis=0) - xy.min(axis=0)
    span = np.maximum(span, 1.0)
    scale = min(max_width_px / span[0], max_height_px / span[1])
    pixels = (xy - xy.min(axis=0)) * scale
    width = max(1, int(np.ceil(pixels[:, 0].max())) + stroke_px * 2)
    height = max(1, int(np.ceil(pixels[:, 1].max())) + stroke_px * 2)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pen = max(1, stroke_px)
    stroke: list[tuple[float, float]] = []
    for x, y, eos in np.concatenate([pixels, coords[:, 2:3]], axis=1):
        stroke.append((float(x) + pen, float(y) + pen))
        if eos >= 0.5 and len(stroke) >= 2:
            draw.line(stroke, fill=(29, 29, 31, 255), width=pen, joint="curve")
            stroke = []
        elif eos >= 0.5:
            stroke = []
    if len(stroke) >= 2:
        draw.line(stroke, fill=(29, 29, 31, 255), width=pen, joint="curve")
    return image
