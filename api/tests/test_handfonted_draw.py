"""Repeated characters use a different saved drawing."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from app.handwriting.handfonted_draw import render_varied, use_glyphs


def _png(size: tuple[int, int], box: tuple[int, int, int, int]) -> bytes:
    image = Image.new("L", size, 0)
    pixels = image.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            pixels[x, y] = 255
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _ink_width(image: Image.Image) -> int:
    mask = image.getchannel("A")
    box = mask.getbbox()
    assert box is not None
    return box[2] - box[0]


def _ink_rows(image: Image.Image, x0: int, x1: int) -> tuple[int, int] | None:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    rows = [
        y for y in range(image.height)
        if any(pixels[x, y] > 30 for x in range(max(0, x0), min(image.width, x1)))
    ]
    if not rows:
        return None
    return rows[0], rows[-1]


def _bands(image: Image.Image) -> list[tuple[int, int]]:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    runs: list[tuple[int, int]] = []
    start = None
    for x in range(image.width):
        ink = any(pixels[x, y] > 30 for y in range(image.height))
        if ink and start is None:
            start = x
        elif not ink and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, image.width))
    return runs


def test_each_copy_of_a_letter_can_be_chosen(tmp_path: Path) -> None:
    narrow = tmp_path / "narrow.png"
    wide = tmp_path / "wide.png"
    narrow.write_bytes(_png((12, 40), (4, 2, 8, 38)))
    wide.write_bytes(_png((40, 16), (2, 4, 38, 12)))
    glyphs = [
        {"id": "narrow", "label": "e", "kept": True, "sample": 1},
        {"id": "wide", "label": "e", "kept": True, "sample": 2},
    ]
    widths = []
    for seed in (0, 1):
        with use_glyphs(tmp_path, glyphs):
            image = render_varied("e", max_width_px=400, max_height_px=200, font_size_pt=28, dpi=96, seed=seed, line_gap_px=4)
        assert image is not None
        widths.append(_ink_width(image))
    assert len(set(widths)) == 2


def test_a_word_moves_to_the_next_line_whole(tmp_path: Path) -> None:
    glyph = tmp_path / "i.png"
    glyph.write_bytes(_png((20, 20), (2, 2, 18, 18)))
    glyphs = [{"id": "i", "label": "i", "kept": True, "sample": 1}]
    with use_glyphs(tmp_path, glyphs):
        image = render_varied(
            "ii ii",
            max_width_px=70,
            max_height_px=400,
            font_size_pt=28,
            dpi=96,
            seed=1,
            line_gap_px=8,
        )
    assert image is not None
    alpha = image.getchannel("A")
    pixels = alpha.load()
    rows = [y for y in range(image.height) if any(pixels[x, y] > 30 for x in range(image.width))]
    gaps = [index for index in range(1, len(rows)) if rows[index] > rows[index - 1] + 1]
    assert gaps, "the second word should sit on the next line"
    split = rows[gaps[0] - 1]
    top = _bands(image.crop((0, 0, image.width, split + 1)))
    bottom = _bands(image.crop((0, split + 1, image.width, image.height)))
    assert len(top) == 2
    assert len(bottom) == 2


def test_repeated_letters_in_one_word_share_a_drawing(tmp_path: Path) -> None:
    narrow = tmp_path / "narrow.png"
    wide = tmp_path / "wide.png"
    narrow.write_bytes(_png((10, 40), (3, 2, 7, 38)))
    wide.write_bytes(_png((40, 40), (2, 2, 38, 38)))
    glyphs = [
        {"id": "narrow", "label": "p", "kept": True, "sample": 1},
        {"id": "wide", "label": "p", "kept": True, "sample": 2},
    ]
    with use_glyphs(tmp_path, glyphs):
        same = render_varied("pp", max_width_px=500, max_height_px=300, font_size_pt=28, dpi=96, seed=0, line_gap_px=6)
        split = render_varied("p p", max_width_px=500, max_height_px=300, font_size_pt=28, dpi=96, seed=0, line_gap_px=6)
    assert same is not None and split is not None
    same_runs = _bands(same)
    split_runs = _bands(split)
    assert len(same_runs) == 2
    assert len(split_runs) == 2
    left = same_runs[0][1] - same_runs[0][0]
    right = same_runs[1][1] - same_runs[1][0]
    assert abs(left - right) <= 2
    split_left = split_runs[0][1] - split_runs[0][0]
    split_right = split_runs[1][1] - split_runs[1][0]
    assert abs(split_left - split_right) > 4


def test_word_spacing_does_not_change_between_cards(tmp_path: Path) -> None:
    glyph = tmp_path / "n.png"
    glyph.write_bytes(_png((24, 24), (2, 2, 22, 22)))
    glyphs = [{"id": "n", "label": "n", "kept": True, "sample": 1}]
    gaps = []
    for seed in (0, 7):
        with use_glyphs(tmp_path, glyphs):
            image = render_varied("n n", max_width_px=400, max_height_px=200, font_size_pt=28, dpi=96, seed=seed, line_gap_px=6)
        assert image is not None
        runs = _bands(image)
        assert len(runs) == 2
        gaps.append(runs[1][0] - runs[0][1])
    assert gaps[0] == gaps[1]


def test_letters_share_a_baseline_and_keep_their_heights(tmp_path: Path) -> None:
    for name, size in (("i", (20, 20)), ("b", (12, 40)), ("g", (12, 40))):
        (tmp_path / f"{name}.png").write_bytes(_png(size, (1, 1, size[0] - 1, size[1] - 1)))
    glyphs = [
        {"id": "i", "label": "i", "kept": True, "sample": 1},
        {"id": "b", "label": "b", "kept": True, "sample": 1},
        {"id": "g", "label": "g", "kept": True, "sample": 1},
    ]
    with use_glyphs(tmp_path, glyphs):
        image = render_varied("ibg", max_width_px=400, max_height_px=300, font_size_pt=32, dpi=96, seed=2, line_gap_px=4)
    assert image is not None
    runs = _bands(image)
    assert len(runs) == 3
    eye = _ink_rows(image, *runs[0])
    bee = _ink_rows(image, *runs[1])
    gee = _ink_rows(image, *runs[2])
    assert eye is not None and bee is not None and gee is not None
    assert abs(eye[1] - bee[1]) <= 1
    assert bee[0] < eye[0]
    assert gee[1] > eye[1]


def test_font_punctuation_is_drawn_on_the_baseline(tmp_path: Path) -> None:
    (tmp_path / "i.png").write_bytes(_png((20, 20), (2, 2, 18, 18)))
    glyphs = [{"id": "i", "label": "i", "kept": True, "sample": 1}]
    with use_glyphs(tmp_path, glyphs):
        plain = render_varied("i", max_width_px=400, max_height_px=300, font_size_pt=32, dpi=96, seed=1, line_gap_px=4)
        stopped = render_varied("i.", max_width_px=400, max_height_px=300, font_size_pt=32, dpi=96, seed=1, line_gap_px=4)
        quoted = render_varied('"i', max_width_px=400, max_height_px=300, font_size_pt=32, dpi=96, seed=1, line_gap_px=4)
        noted = render_varied("i, i: i'", max_width_px=500, max_height_px=300, font_size_pt=32, dpi=96, seed=1, line_gap_px=4)
    assert plain is not None and stopped is not None and quoted is not None and noted is not None
    assert _ink_width(stopped) > _ink_width(plain)
    runs = _bands(stopped)
    assert len(runs) >= 2
    eye = _ink_rows(stopped, *runs[0])
    period = _ink_rows(stopped, *runs[-1])
    assert eye is not None and period is not None
    assert (period[1] - period[0]) < (eye[1] - eye[0])
    assert abs(period[1] - eye[1]) <= 4
    quote_runs = _bands(quoted)
    assert len(quote_runs) >= 2
    quote = _ink_rows(quoted, *quote_runs[0])
    assert quote is not None and eye is not None
    assert quote[1] < eye[1]
