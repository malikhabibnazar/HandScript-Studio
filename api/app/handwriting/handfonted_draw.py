"""Draw a page from several real copies of each character.

Copies vary from word to word. Inside one word, a repeated letter uses the
same drawing. Every letter sits on one baseline, at the height its class
requires, and a word moves to the next line as a whole.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = (29, 29, 31, 255)
# These are not collected from the handwriting photo yet. They are drawn from
# the studio handwriting face and sit on the same baseline as the letters.
_FONT_FACE = Path(__file__).resolve().parent / "fonts" / "ArchitectsDaughter-Regular.ttf"
_PUNCT_SOURCE = {
    ",": ",",
    ".": ".",
    ":": ":",
    '"': '"',
    "'": "'",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}
_font_size_for_cap: dict[int, int] = {}
_font_marks: dict[tuple[str, int], tuple[Image.Image, int] | None] = {}
_X_HEIGHT = set("aceimnorsuvwxz")
_ASCENDERS = set("bdfhklt")
_DESCENDERS = set("gjpqy")
_ROUNDED = set("oaces")
_bank: ContextVar["GlyphBank | None"] = ContextVar("handfonted_bank", default=None)


@dataclass
class GlyphBank:
    groups: dict[str, list[Path]]
    cache: dict[Path, Image.Image | None] = field(default_factory=dict)

    def source(self, path: Path) -> Image.Image | None:
        if path not in self.cache:
            image = None
            try:
                with Image.open(path) as opened:
                    image = opened.convert("L")
                    image.load()
            except Exception:
                image = None
            self.cache[path] = image
        return self.cache[path]

    def sprite(self, path: Path, height: int) -> Image.Image | None:
        cached = self.source(path)
        if cached is None:
            return None
        mask = cached.point(lambda pixel: 255 if pixel > 40 else 0)
        box = mask.getbbox()
        if box is None:
            return None
        mask = mask.crop(box)
        height = max(1, int(height))
        width = max(1, int(round(mask.width * height / max(1, mask.height))))
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)
        sprite = Image.new("RGBA", mask.size, (*INK[:3], 0))
        sprite.putalpha(mask)
        return sprite


@contextmanager
def use_glyphs(folder: Path, glyphs: list[dict]):
    groups: dict[str, list[Path]] = {}
    ordered = sorted(
        glyphs,
        key=lambda item: (int(item.get("sample") or 1), str(item.get("id") or "")),
    )
    for item in ordered:
        if item.get("kept", True) is False:
            continue
        label = str(item.get("label") or "")
        glyph_id = str(item.get("id") or "")
        if len(label) != 1 or not glyph_id:
            continue
        path = folder / f"{glyph_id}.png"
        if path.is_file():
            groups.setdefault(label, []).append(path)
    token = _bank.set(GlyphBank(groups))
    try:
        yield
    finally:
        _bank.reset(token)


def _zone(char: str, cap: int, x_height: int, descender: int) -> tuple[int, int]:
    """Return ink height and how far the top sits above the baseline."""
    if char in _DESCENDERS:
        return x_height + descender, x_height
    if char.isupper() or char.isdigit() or char in _ASCENDERS:
        return cap, cap
    if char in _ROUNDED:
        overshoot = max(1, int(round(x_height * 0.06)))
        return x_height + overshoot, x_height + overshoot // 2
    return x_height, x_height


def _font_px(cap: int) -> int:
    cached = _font_size_for_cap.get(cap)
    if cached is not None:
        return cached
    size = cap
    if _FONT_FACE.is_file():
        for _ in range(6):
            font = ImageFont.truetype(str(_FONT_FACE), size=size)
            box = font.getbbox("H")
            ink = max(1, box[3] - box[1])
            if abs(ink - cap) <= 1:
                break
            size = max(8, int(round(size * cap / ink)))
    _font_size_for_cap[cap] = size
    return size


def _font_mark(char: str, cap: int) -> tuple[Image.Image, int] | None:
    source = _PUNCT_SOURCE.get(char)
    if source is None:
        return None
    key = (source, cap)
    if key in _font_marks:
        return _font_marks[key]
    mark: tuple[Image.Image, int] | None = None
    if _FONT_FACE.is_file():
        font = ImageFont.truetype(str(_FONT_FACE), size=_font_px(cap))
        ascent, descent = font.getmetrics()
        origin_y = ascent + 4
        canvas = Image.new("L", (ascent + descent + 16, ascent + descent + 16), 0)
        ImageDraw.Draw(canvas).text((4, origin_y), source, font=font, fill=255, anchor="ls")
        mask = canvas.point(lambda pixel: 255 if pixel > 40 else 0)
        box = mask.getbbox()
        if box is not None:
            cropped = mask.crop(box)
            sprite = Image.new("RGBA", cropped.size, (*INK[:3], 0))
            sprite.putalpha(cropped)
            mark = (sprite, origin_y - box[1])
    _font_marks[key] = mark
    return mark


def _tokens(text: str) -> list[str | None]:
    tokens: list[str | None] = []
    word: list[str] = []

    def flush() -> None:
        if word:
            tokens.append("".join(word))
            word.clear()

    for char in text or "":
        if char == "\n":
            flush()
            tokens.append(None)
        elif char.isspace():
            flush()
        else:
            word.append(char)
    flush()
    return tokens


def render_varied(
    text: str,
    *,
    max_width_px: int,
    max_height_px: int,
    font_size_pt: float,
    dpi: int,
    seed: int | None,
    line_gap_px: int,
) -> Image.Image | None:
    """Return a transparent ink image, or None when no saved drawings are available."""
    bank = _bank.get()
    if bank is None or not bank.groups:
        return None
    cap = max(16, int(float(font_size_pt) * int(dpi) / 72))
    x_height = max(8, int(round(cap * 0.55)))
    descender = max(3, int(round(x_height * 0.40)))
    letter_gap = max(2, int(round(x_height * 0.18)))
    line_gap = max(0, int(line_gap_px))
    stride = cap + descender + line_gap
    width_limit = max(8, int(max_width_px))
    height_limit = max(stride, int(max_height_px))
    page_seed = 0 if seed is None else int(seed)

    def draw(char: str, path: Path | None) -> Image.Image | None:
        if path is None:
            return None
        height, _rise = _zone(char, cap, x_height, descender)
        return bank.sprite(path, height)

    word_gap = x_height
    for label in ("n", "o"):
        copies = bank.groups.get(label)
        if not copies:
            continue
        sample = draw(label, copies[0])
        if sample is not None:
            word_gap = sample.width
            break

    def piece(char: str, chosen: dict[str, tuple[Image.Image, int] | None]) -> tuple[Image.Image, int] | None:
        if char not in chosen:
            copies = bank.groups.get(char) or []
            if copies:
                start = (page_seed + ord(char)) % len(copies)
                path = copies[(start + word_index[0]) % len(copies)]
                height, rise = _zone(char, cap, x_height, descender)
                sprite = bank.sprite(path, height)
                chosen[char] = None if sprite is None else (sprite, rise)
            elif char in _PUNCT_SOURCE:
                chosen[char] = _font_mark(char, cap)
            else:
                chosen[char] = None
        return chosen[char]

    word_index = [0]

    def between(before: str, after: str) -> int:
        if before in _PUNCT_SOURCE or after in _PUNCT_SOURCE:
            return max(1, letter_gap // 3)
        return letter_gap

    def measure(word: str) -> tuple[int, list[tuple[Image.Image, int] | None]]:
        chosen: dict[str, tuple[Image.Image, int] | None] = {}
        parts = [piece(char, chosen) for char in word]
        width = 0
        for index, part in enumerate(parts):
            if index:
                width += between(word[index - 1], word[index])
            width += part[0].width if part is not None else max(1, x_height // 2)
        return width, parts

    placed: list[tuple[int, int, Image.Image]] = []
    x = 0
    y = 0
    gap_before = False

    def newline() -> bool:
        nonlocal x, y, gap_before
        if y + stride > height_limit:
            return False
        x = 0
        y += stride
        gap_before = False
        return y + cap <= height_limit

    for token in _tokens(text):
        if token is None:
            if not newline() and y > 0:
                break
            continue
        width, parts = measure(token)
        word_index[0] += 1
        needed = width + (word_gap if gap_before and x > 0 else 0)
        if x > 0 and x + needed > width_limit:
            if not newline():
                break
        if gap_before and x > 0:
            x += word_gap
        cursor = x
        baseline = y + cap
        for index, (char, part) in enumerate(zip(token, parts)):
            if index:
                cursor += between(token[index - 1], char)
            if part is None:
                cursor += max(1, x_height // 2)
                continue
            sprite, rise = part
            placed.append((cursor, baseline - rise, sprite))
            cursor += sprite.width
        x = cursor
        gap_before = True

    if not placed:
        return None
    height = max(1, min(height_limit, y + cap + descender))
    image = Image.new("RGBA", (width_limit, height), (0, 0, 0, 0))
    for left, top, sprite in placed:
        if top >= height or left >= width_limit:
            continue
        clipped = sprite
        overflow_x = left + sprite.width - width_limit
        overflow_y = top + sprite.height - height
        if overflow_x > 0 or overflow_y > 0 or top < 0:
            crop_top = max(0, -top)
            crop_bottom = sprite.height - max(0, overflow_y)
            crop_right = sprite.width - max(0, overflow_x)
            if crop_bottom <= crop_top or crop_right <= 0:
                continue
            clipped = sprite.crop((0, crop_top, crop_right, crop_bottom))
            top = max(0, top)
        image.alpha_composite(clipped, (max(0, left), top))
    return image
