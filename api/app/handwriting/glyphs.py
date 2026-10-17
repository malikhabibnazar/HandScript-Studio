"""Drawn-letter storage. Each character is its own PNG. Nothing here joins strokes."""
from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.storage import get_storage

PAD_WIDTH = 280
PAD_HEIGHT = 220
BASELINE_Y = 150
SETS = ("set1", "set2")
_CORE_MARKS = set(".,'-")

_MARKS: list[tuple[str, str]] = [
    (".", "period"),
    (",", "comma"),
    ("!", "exclaim"),
    ("?", "question"),
    ("'", "apostrophe"),
    ('"', "quote"),
    (":", "colon"),
    (";", "semicolon"),
    ("-", "hyphen"),
    ("(", "lparen"),
    (")", "rparen"),
    ("/", "slash"),
    ("&", "ampersand"),
    ("@", "at"),
    ("#", "hash"),
    ("$", "dollar"),
    ("%", "percent"),
    ("+", "plus"),
    ("=", "equal"),
    ("*", "star"),
    ("[", "lbracket"),
    ("]", "rbracket"),
    ("{", "lbrace"),
    ("}", "rbrace"),
    ("<", "lt"),
    (">", "gt"),
    ("`", "backtick"),
    ("_", "underscore"),
]


@dataclass(frozen=True)
class GlyphSpec:
    key: str
    char: str
    group: str


def _catalog() -> list[GlyphSpec]:
    # Letter keys carry a case prefix. Windows storage treats A.png and a.png as one file.
    rows: list[GlyphSpec] = [GlyphSpec(f"upper-{char}", char, "uppercase") for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    rows.extend(GlyphSpec(f"lower-{char}", char, "lowercase") for char in "abcdefghijklmnopqrstuvwxyz")
    rows.extend(GlyphSpec(char, char, "symbols") for char in "0123456789")
    rows.extend(GlyphSpec(key, char, "symbols") for char, key in _MARKS)
    return rows


CATALOG: list[GlyphSpec] = _catalog()
BY_KEY: dict[str, GlyphSpec] = {spec.key: spec for spec in CATALOG}
BY_CHAR: dict[str, GlyphSpec] = {spec.char: spec for spec in CATALOG}
CORE_KEYS: frozenset[str] = frozenset(spec.key for spec in CATALOG if spec.char.isalnum() or spec.char in _CORE_MARKS)

if len(CATALOG) != 90 or len(BY_KEY) != 90:
    raise RuntimeError(f"Drawn alphabet must contain 90 characters, found {len(CATALOG)}")


def spec_for_key(key: str) -> GlyphSpec | None:
    return BY_KEY.get(key)


def _png_key(profile_id: str, set_name: str, key: str) -> str:
    return f"glyphs/{profile_id}/{set_name}/{key}.png"


def _meta_key(profile_id: str, set_name: str, key: str) -> str:
    return f"glyphs/{profile_id}/{set_name}/{key}.json"


def _check_set(set_name: str) -> str:
    if set_name not in SETS:
        raise ValueError("set must be set1 or set2")
    return set_name


_PRINT_FONT: ImageFont.ImageFont | None = None


def _print_font(size: int) -> ImageFont.ImageFont:
    global _PRINT_FONT
    if _PRINT_FONT is not None:
        return _PRINT_FONT
    for path in (
        r"C:\Windows\Fonts\segoepr.ttf",
        r"C:\Windows\Fonts\comic.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(path).exists():
            _PRINT_FONT = ImageFont.truetype(path, size=max(12, size))
            return _PRINT_FONT
    _PRINT_FONT = ImageFont.load_default()
    return _PRINT_FONT


def rasterize_sample(char: str) -> tuple[bytes, dict]:
    """One print-style character on the shared pad. The font is only a starter set."""
    image = Image.new("RGBA", (PAD_WIDTH, PAD_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _print_font(78)
    try:
        ascent, _descent = font.getmetrics()
    except Exception:
        ascent = 62
    draw.text((36, BASELINE_Y - int(ascent)), char, fill=(29, 29, 31, 255), font=font)
    if image.getbbox() is None:
        draw.ellipse((36, BASELINE_Y - 4, 44, BASELINE_Y + 4), fill=(29, 29, 31, 255))
    bbox = image.getbbox()
    assert bbox is not None
    crop = image.crop(bbox)
    metrics = {
        "pad_width": PAD_WIDTH,
        "pad_height": PAD_HEIGHT,
        "baseline_y": BASELINE_Y,
        "crop_left": int(bbox[0]),
        "crop_top": int(bbox[1]),
        "ink_width": int(crop.width),
        "ink_height": int(crop.height),
    }
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return buf.getvalue(), metrics


def _stored_names(profile_id: str) -> set[str]:
    prefix = f"glyphs/{profile_id}/"
    return {key for key, _size in get_storage().list_prefix(prefix)}


def _read_pair(profile_id: str, set_name: str, key: str) -> tuple[bytes, dict] | None:
    names = _stored_names(profile_id)
    png = _png_key(profile_id, set_name, key)
    meta_path = _meta_key(profile_id, set_name, key)
    if png not in names or meta_path not in names:
        return None
    store = get_storage()
    try:
        raw = store.get(png)
        meta = json.loads(store.get(meta_path).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    return raw, meta


def load_pairs(profile_id: str) -> list[tuple[str, str, bytes, dict]]:
    if not profile_id:
        return []
    names = _stored_names(profile_id)
    store = get_storage()
    rows: list[tuple[str, str, bytes, dict]] = []
    for set_name in SETS:
        for spec in CATALOG:
            png = _png_key(profile_id, set_name, spec.key)
            meta_path = _meta_key(profile_id, set_name, spec.key)
            if png not in names or meta_path not in names:
                continue
            try:
                meta = json.loads(store.get(meta_path).decode("utf-8"))
                raw = store.get(png)
            except Exception:
                continue
            if isinstance(meta, dict):
                rows.append((set_name, spec.key, raw, meta))
    return rows


def _metrics_out(meta: dict) -> dict | None:
    try:
        return {
            "pad_width": int(meta["pad_width"]),
            "pad_height": int(meta["pad_height"]),
            "baseline_y": float(meta["baseline_y"]),
            "crop_left": int(meta["crop_left"]),
            "crop_top": int(meta["crop_top"]),
            "ink_width": int(meta["ink_width"]),
            "ink_height": int(meta["ink_height"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def inventory(profile_id: str) -> dict:
    stored = {(set_name, key): meta for set_name, key, _raw, meta in load_pairs(profile_id)}
    slots = []
    set1_count = 0
    set2_count = 0
    present: dict[str, set[str]] = {"set1": set(), "set2": set()}
    for spec in CATALOG:
        slot: dict = {"key": spec.key, "char": spec.char, "group": spec.group, "set1": None, "set2": None}
        for set_name in SETS:
            meta = stored.get((set_name, spec.key))
            if meta is None:
                continue
            metrics = _metrics_out(meta)
            if metrics is None:
                continue
            slot[set_name] = metrics
            present[set_name].add(spec.key)
        if slot["set1"] is not None:
            set1_count += 1
        if slot["set2"] is not None:
            set2_count += 1
        slots.append(slot)
    return {
        "total": len(CATALOG),
        "set1_count": set1_count,
        "set2_count": set2_count,
        "ready": CORE_KEYS <= present["set1"],
        "pad_width": PAD_WIDTH,
        "pad_height": PAD_HEIGHT,
        "baseline_y": BASELINE_Y,
        "slots": slots,
    }


def glyphs_ready(profile_id: str) -> bool:
    return bool(inventory(profile_id)["ready"])


def normalize_metrics(
    *,
    baseline_y: float,
    pad_width: int,
    pad_height: int,
    crop_left: int,
    crop_top: int,
    ink_width: int,
    ink_height: int,
) -> dict:
    width = int(pad_width)
    height = int(pad_height)
    if width < 32 or height < 32 or width > 800 or height > 800:
        raise ValueError("pad size is out of range")
    return {
        "pad_width": width,
        "pad_height": height,
        "baseline_y": min(float(height), max(0.0, float(baseline_y))),
        "crop_left": max(0, int(crop_left)),
        "crop_top": max(0, int(crop_top)),
        "ink_width": max(1, int(ink_width)),
        "ink_height": max(1, int(ink_height)),
    }


def save_glyph(
    profile_id: str,
    set_name: str,
    key: str,
    raw: bytes,
    *,
    baseline_y: float,
    pad_width: int,
    pad_height: int,
    crop_left: int,
    crop_top: int,
) -> None:
    _check_set(set_name)
    if spec_for_key(key) is None:
        raise ValueError("unknown character")
    if not raw or len(raw) > 1_500_000:
        raise ValueError("drawing must be a PNG under 1.5 MB")
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception as exc:
        raise ValueError("drawing is not a PNG") from exc
    if image.width > 800 or image.height > 800 or image.width < 1 or image.height < 1:
        raise ValueError("drawing is too large")
    metrics = normalize_metrics(
        baseline_y=baseline_y,
        pad_width=pad_width,
        pad_height=pad_height,
        crop_left=crop_left,
        crop_top=crop_top,
        ink_width=image.width,
        ink_height=image.height,
    )
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    store = get_storage()
    store.put(_png_key(profile_id, set_name, key), buf.getvalue(), "image/png")
    store.put(_meta_key(profile_id, set_name, key), json.dumps(metrics).encode("utf-8"), "application/json")


def read_glyph_png(profile_id: str, set_name: str, key: str) -> bytes | None:
    _check_set(set_name)
    if spec_for_key(key) is None:
        raise ValueError("unknown character")
    pair = _read_pair(profile_id, set_name, key)
    if pair is None:
        return None
    return pair[0]


def delete_glyph(profile_id: str, set_name: str, key: str) -> None:
    _check_set(set_name)
    if spec_for_key(key) is None:
        raise ValueError("unknown character")
    store = get_storage()
    store.delete(_png_key(profile_id, set_name, key))
    store.delete(_meta_key(profile_id, set_name, key))


def clear_glyphs(profile_id: str) -> None:
    get_storage().delete_prefix(f"glyphs/{profile_id}/")


def restore_sample(profile_id: str) -> None:
    """Replace set 1 with the bundled print alphabet. Set 2 is left as the user drew it."""
    store = get_storage()
    for spec in CATALOG:
        raw, metrics = rasterize_sample(spec.char)
        store.put(_png_key(profile_id, "set1", spec.key), raw, "image/png")
        store.put(_meta_key(profile_id, "set1", spec.key), json.dumps(metrics).encode("utf-8"), "application/json")
