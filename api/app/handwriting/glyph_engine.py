"""Place drawn letters one at a time. There is no ligature map and no stroke between letters."""
from __future__ import annotations

import io
import math
import random
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from PIL import Image, ImageDraw

from app.handwriting.glyphs import BY_CHAR, BASELINE_Y, PAD_HEIGHT, load_pairs

_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
_job: ContextVar["GlyphJob | None"] = ContextVar("glyph_job", default=None)


@dataclass
class GlyphJob:
    images: dict[tuple[str, str], Image.Image]
    metrics: dict[tuple[str, str], dict]
    word_size_px: float = 70
    word_spacing_px: float = 15
    char_spacing_px: float = -2.5
    ink_color: str | None = None


@contextmanager
def use_glyphs(job: GlyphJob):
    token = _job.set(job)
    try:
        yield
    finally:
        _job.reset(token)


def current_job() -> GlyphJob | None:
    return _job.get()


def choose_set(index: int, key: str, seed: int, has_set1: bool, has_set2: bool) -> str | None:
    """Set 2 is another drawing of the same letter, never a join."""
    if has_set1 and has_set2:
        rng = random.Random((seed * 1_315_423_911) ^ (index * 2_654_435_761) ^ sum(ord(char) for char in key))
        return "set2" if rng.random() < 0.5 else "set1"
    if has_set1:
        return "set1"
    if has_set2:
        return "set2"
    return None


def _gap(char_spacing_px: float, word_size_px: float, target_em: float) -> int:
    raw = char_spacing_px * (target_em / max(word_size_px, 1))
    floor = max(2.0, target_em * 0.03)
    return int(math.ceil(max(raw, floor)))


def _word_gap(word_spacing_px: float, word_size_px: float, target_em: float) -> int:
    raw = word_spacing_px * (target_em / max(word_size_px, 1))
    floor = max(8.0, target_em * 0.12)
    return int(math.ceil(max(raw, floor)))


def _missing_gap(char_spacing_px: float, word_size_px: float, target_em: float) -> int:
    return max(_gap(char_spacing_px, word_size_px, target_em), int(math.ceil(target_em * 0.38)))


def _tint(image: Image.Image, color: str | None) -> Image.Image:
    if not color or not _COLOR.fullmatch(color):
        return image
    rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    solid = Image.new("RGBA", image.size, (*rgb, 255))
    solid.putalpha(image.getchannel("A"))
    return solid


def _rotate(image: Image.Image, degrees: float, anchor_x: float, anchor_y: float) -> tuple[Image.Image, float, float]:
    if abs(degrees) < 0.05:
        return image, anchor_x, anchor_y
    width, height = image.size
    side = int(math.hypot(width, height)) + 4
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    origin_x = (side - width) // 2
    origin_y = (side - height) // 2
    canvas.paste(image, (origin_x, origin_y), image)
    center = (origin_x + anchor_x, origin_y + anchor_y)
    rotated = canvas.rotate(degrees, resample=Image.Resampling.BICUBIC, center=center)
    bbox = rotated.getbbox()
    if bbox is None:
        return image, anchor_x, anchor_y
    cropped = rotated.crop(bbox)
    return cropped, center[0] - bbox[0], center[1] - bbox[1]


def _lookup(job: GlyphJob, char: str, index: int, seed: int) -> tuple[Image.Image, dict] | None:
    spec = BY_CHAR.get(char)
    if spec is None:
        return None
    has_set1 = ("set1", spec.key) in job.images
    has_set2 = ("set2", spec.key) in job.images
    chosen = choose_set(index, spec.key, seed, has_set1, has_set2)
    if chosen is None:
        return None
    return job.images[(chosen, spec.key)], job.metrics[(chosen, spec.key)]


def _ink_width(metrics: dict, target_em: float) -> int:
    pad_height = max(1, int(metrics.get("pad_height") or PAD_HEIGHT))
    scale = target_em / pad_height
    return max(1, int(round(int(metrics["ink_width"]) * scale)))


def _measure(text: str, job: GlyphJob, target_em: float) -> int:
    char_gap = _gap(job.char_spacing_px, job.word_size_px, target_em)
    word_gap = _word_gap(job.word_spacing_px, job.word_size_px, target_em)
    width = 0
    for index, char in enumerate(text):
        if char == " ":
            width += word_gap
            continue
        found = _lookup(job, char, index, 0)
        piece = _ink_width(found[1], target_em) if found else _missing_gap(job.char_spacing_px, job.word_size_px, target_em)
        width += piece
        if index < len(text) - 1 and text[index + 1] != " ":
            width += char_gap
    return width


def _wrap(text: str, job: GlyphJob, target_em: float, max_width: int) -> list[str]:
    lines: list[str] = []
    limit = max(8, max_width)
    for paragraph in (text or "").split("\n"):
        if paragraph == "":
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            pieces = _split_word(word, job, target_em, limit)
            for piece in pieces:
                trial = piece if not current else f"{current} {piece}"
                if not current or _measure(trial, job, target_em) <= limit:
                    current = trial
                else:
                    lines.append(current)
                    current = piece
        lines.append(current)
    return lines or [""]


def _split_word(word: str, job: GlyphJob, target_em: float, limit: int) -> list[str]:
    if not word or _measure(word, job, target_em) <= limit:
        return [word]
    pieces: list[str] = []
    token = ""
    for char in word:
        trial = token + char
        if not token or _measure(trial, job, target_em) <= limit:
            token = trial
        else:
            pieces.append(token)
            token = char
    if token:
        pieces.append(token)
    return pieces or [""]


def _place(
    image: Image.Image,
    glyph: Image.Image,
    metrics: dict,
    *,
    cursor: int,
    baseline: float,
    target_em: float,
    amount: float,
    rng: random.Random,
) -> tuple[int, int]:
    pad_height = max(1.0, float(metrics.get("pad_height") or PAD_HEIGHT))
    scale = (target_em / pad_height) * (1 + rng.uniform(-0.04, 0.04) * amount)
    width = max(1, int(round(glyph.width * scale)))
    height = max(1, int(round(glyph.height * scale)))
    resized = glyph.resize((width, height), Image.Resampling.LANCZOS)
    base_x = width / 2
    base_y = (float(metrics["baseline_y"]) - float(metrics["crop_top"])) * scale
    turned, base_x, base_y = _rotate(resized, rng.uniform(-1.5, 1.5) * amount, base_x, base_y)
    drift = rng.uniform(-2.0, 2.0) * (target_em / 70) * amount
    paste_x = cursor
    paste_y = int(round(baseline - base_y + drift))
    image.paste(turned, (paste_x, paste_y), turned)
    return turned.width, paste_x


def compose_ink(
    text: str,
    job: GlyphJob,
    *,
    target_em: float,
    max_width: int,
    max_height: int,
    seed: int,
    variation: float,
    line_gap_px: int,
) -> Image.Image:
    image, _baselines = compose_ink_meta(
        text,
        job,
        target_em=target_em,
        max_width=max_width,
        max_height=max_height,
        seed=seed,
        variation=variation,
        line_gap_px=line_gap_px,
    )
    return image


def compose_ink_meta(
    text: str,
    job: GlyphJob,
    *,
    target_em: float,
    max_width: int,
    max_height: int,
    seed: int,
    variation: float,
    line_gap_px: int,
) -> tuple[Image.Image, list[float]]:
    target_em = max(8.0, float(target_em))
    lines = _wrap(text, job, target_em, max(8, max_width))
    ascender = target_em * (BASELINE_Y / PAD_HEIGHT)
    descender = target_em * ((PAD_HEIGHT - BASELINE_Y) / PAD_HEIGHT)
    step = target_em + max(0, line_gap_px)
    height = int(math.ceil(ascender + descender + max(0, len(lines) - 1) * step))
    height = max(1, min(max_height, height))
    width = max(1, max_width)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    amount = 0.0 if variation <= 0 else min(1.0, variation / 0.15)
    char_gap = _gap(job.char_spacing_px, job.word_size_px, target_em)
    word_gap = _word_gap(job.word_spacing_px, job.word_size_px, target_em)
    baselines: list[float] = []
    cursor_index = 0
    for line_index, line in enumerate(lines):
        baseline = ascender + line_index * step
        if baseline > height:
            break
        baselines.append(baseline)
        cursor = 0
        previous = ""
        for char in line:
            if cursor >= width:
                break
            if char == " ":
                cursor += word_gap
                previous = char
                cursor_index += 1
                continue
            found = _lookup(job, char, cursor_index, seed)
            if previous and previous != " ":
                cursor += char_gap
            if found is None:
                cursor += _missing_gap(job.char_spacing_px, job.word_size_px, target_em)
            else:
                glyph = _tint(found[0], job.ink_color)
                rng = random.Random((seed * 97) ^ (cursor_index * 1_234) ^ ord(char))
                placed, _paste_x = _place(
                    image, glyph, found[1],
                    cursor=cursor, baseline=baseline, target_em=target_em, amount=amount, rng=rng,
                )
                cursor += placed
            previous = char
            cursor_index += 1
    return image, baselines


def load_glyph_job(
    profile_id: str,
    *,
    word_size_px: float,
    word_spacing_px: float,
    char_spacing_px: float,
    ink_color: str | None,
) -> GlyphJob:
    images: dict[tuple[str, str], Image.Image] = {}
    metrics: dict[tuple[str, str], dict] = {}
    for set_name, key, raw, meta in load_pairs(profile_id):
        try:
            images[(set_name, key)] = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            continue
        metrics[(set_name, key)] = meta
    return GlyphJob(
        images=images,
        metrics=metrics,
        word_size_px=float(word_size_px or 70),
        word_spacing_px=float(word_spacing_px or 15),
        char_spacing_px=float(char_spacing_px),
        ink_color=ink_color or None,
    )


def render_ruled_preview(text: str, job: GlyphJob, *, seed: int = 1, variation: float = 0.15) -> bytes:
    target = max(24.0, float(job.word_size_px))
    ink, baselines = compose_ink_meta(
        text or "",
        job,
        target_em=target,
        max_width=700,
        max_height=900,
        seed=seed,
        variation=variation,
        line_gap_px=max(8, int(target * 0.28)),
    )
    width = 760
    height = max(320, ink.height + 56)
    paper = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(paper)
    for baseline in baselines:
        y = int(round(28 + baseline))
        draw.line((20, y, width - 20, y), fill=(186, 210, 232), width=1)
    paper.paste(ink, (32, 28), ink)
    buf = io.BytesIO()
    paper.save(buf, format="PNG")
    return buf.getvalue()


class GlyphEngine:
    name = "drawn"

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
        del style_id, bias
        return self.render_wrapped(
            text,
            max_width_px=max_width_px,
            max_height_px=max_height_px,
            style_id=None,
            bias=0.0,
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
        del style_id, bias
        job = current_job()
        if job is None:
            return Image.new("RGBA", (max(1, max_width_px), 1), (0, 0, 0, 0))
        target_em = max(8.0, float(font_size_pt) * max(1, dpi) / 72)
        return compose_ink(
            text,
            job,
            target_em=target_em,
            max_width=max(1, max_width_px),
            max_height=max(1, max_height_px),
            seed=0 if seed is None else seed,
            variation=variation,
            line_gap_px=line_gap_px,
        )
