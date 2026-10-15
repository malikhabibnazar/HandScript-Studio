"""HandwritingAgent profile renderer.

A profile that selects this engine sends the uploaded handwriting photo and
the exact card text to Gemini. The model must answer with pen strokes only.
A reply whose words differ from the card text is discarded. This engine does
not substitute a built-in font.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from PIL import Image, ImageDraw

from app.config import get_settings

INK = (29, 29, 31, 255)
_samples: ContextVar[tuple[bytes, ...]] = ContextVar("gemini_samples", default=())
_chosen_model: str | None = None
_MODEL_CHAIN = (
    "gemini-3.1-pro-preview",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
)

SYSTEM_PROMPT = """You are HandwritingAgent. You imitate one person's handwriting by drawing pen strokes. You do not author text.

The user message contains TARGET, which is the only text you may write, and one or more photos of that person's real handwriting.

Rules:
- Write TARGET character for character, in the same order. Keep every digit, leading zero, space, capital letter, punctuation mark, and line break.
- Do not add a greeting, date, signature, underline, doodle, border, label, or any word that is not in TARGET.
- Do not correct spelling, expand abbreviations, translate, drop characters, or improve the wording.
- Copy slant, pressure, letter shapes, joins, spacing, and baseline from the photos. When TARGET uses a character the photos do not show, build that character from the same pen, slant, and proportions. Do not switch to a printed or computer font.
- Draw the path of the pen tip, the way a person writes. Do not trace a hollow outline around a printed letter.
- Reply with XML only. No markdown, no commentary, and no SVG <text> or <tspan> elements.
- The canvas is a 1000 by 1000 grid. The origin is the top-left corner. x increases to the right and y increases downward. Keep a small margin.
- Emit one <line> for each line of TARGET, in order. The text attribute is that line exactly. Escape &, <, >, and quotes in XML.
- Each <stroke> uses a d attribute of M, L, Q, and C commands only, in the 1000 grid. width is the pen width on that grid, between 2 and 8.
- The verbatim body must equal TARGET exactly. Joining the line text attributes with newlines must also equal TARGET exactly.

Shape:
<handwriting>
<verbatim>A1</verbatim>
<line text="A1">
<stroke width="4" d="M 80 180 Q 120 140 160 190"/>
</line>
</handwriting>

The letters A1 above are only a format example. Never write them unless they are the user's TARGET.
"""


class GeminiEngine:
    name = "gemini"

    def render_line(self, text: str, **kwargs) -> Image.Image:
        return self.render_wrapped(text, line_gap_px=kwargs.pop("line_gap_px", 4), **kwargs)

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
        del style_id, bias, variation, font_size_pt, dpi, seed, line_gap_px
        return render_handwriting(text, max(1, int(max_width_px)), max(1, int(max_height_px)))


@contextmanager
def use_samples(blobs: list[bytes]):
    token = _samples.set(tuple(blobs))
    try:
        yield
    finally:
        _samples.reset(token)


def render_handwriting(text: str, width: int, height: int) -> Image.Image:
    target = text.replace("\r\n", "\n").replace("\r", "\n")
    blobs = list(_samples.get())
    if not blobs:
        raise RuntimeError(
            "HandwritingAgent needs a handwriting photo on this profile. Upload a sample, then render again."
        )
    images = _prepare_images(blobs)
    if not images:
        raise RuntimeError(
            "HandwritingAgent could not read the uploaded sample. Upload a PNG or JPEG of the handwriting."
        )
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        raise RuntimeError("HandwritingAgent is not configured. Set GEMINI_API_KEY on the API server.")

    api_key = settings.gemini_api_key.strip()
    errors: list[str] = []
    for model in _models_to_try(settings.gemini_model):
        cached = _cache_path(target, images, width, height, model)
        if cached.exists():
            _remember_model(model)
            return Image.open(cached).convert("RGBA")
        try:
            lines = _strokes_for_model(target, images, model, api_key)
        except ValueError as exc:
            errors.append(f"{model} did not keep the card text ({exc})")
            _forget_model(model)
            continue
        except RuntimeError as exc:
            if _retryable(str(exc)):
                errors.append(str(exc))
                _forget_model(model)
                continue
            raise
        image = strokes_to_image(lines, width, height)
        if image.getchannel("A").getextrema()[1] == 0:
            errors.append(f"{model} returned no ink")
            _forget_model(model)
            continue
        _remember_model(model)
        cached.parent.mkdir(parents=True, exist_ok=True)
        image.save(cached, format="PNG")
        return image
    detail = errors[-1] if errors else "Gemini did not return a drawing."
    raise RuntimeError(f"HandwritingAgent could not draw this text. {detail}")


def _models_to_try(configured: str) -> list[str]:
    ordered: list[str] = []
    if _chosen_model:
        ordered.append(_chosen_model)
    for name in ((configured or "").strip(), *_MODEL_CHAIN):
        if name and name not in ordered:
            ordered.append(name)
    return ordered


def _remember_model(model: str) -> None:
    global _chosen_model
    _chosen_model = model


def _forget_model(model: str) -> None:
    global _chosen_model
    if _chosen_model == model:
        _chosen_model = None


def _retryable(message: str) -> bool:
    text = message.lower()
    return any(
        piece in text
        for piece in (
            "high demand",
            "quota",
            "rate limit",
            "rate-limit",
            "not available",
            "no longer available",
            "could not reach gemini",
            "timed out",
            "timeout",
        )
    )


def _strokes_for_model(target: str, images: list[tuple[str, str]], model: str, api_key: str):
    reply = _request_strokes(target, images, model, api_key)
    try:
        return parse_handwriting(reply, target)
    except ValueError as first_error:
        reply = _request_strokes(target, images, model, api_key, correction=str(first_error))
        return parse_handwriting(reply, target)


def parse_handwriting(payload: str, target: str) -> list[list[tuple[list[tuple[float, float]], float]]]:
    xml_text = _extract_xml(payload)
    if re.search(r"<\s*(?:text|tspan)\b", xml_text, re.I):
        raise ValueError("Reply used text elements instead of pen strokes.")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("Reply was not valid handwriting XML.") from exc

    verbatim = "".join(root.findtext("verbatim") or "")
    expected = _lines(target)
    if _lines(verbatim) != expected:
        raise ValueError("The reply did not repeat the card text exactly.")

    line_nodes = [node for node in root if _tag(node) == "line"]
    found: list[str] = []
    for node in line_nodes:
        pieces = _lines(node.attrib.get("text", ""))
        if len(pieces) != 1:
            raise ValueError("Each stroke line must contain one line of the card text.")
        found.append(pieces[0])
    if found != expected:
        raise ValueError("The stroke lines do not match the card text exactly.")

    lines: list[list[tuple[list[tuple[float, float]], float]]] = []
    for node in line_nodes:
        strokes: list[tuple[list[tuple[float, float]], float]] = []
        for stroke in node:
            if _tag(stroke) != "stroke":
                continue
            width = _pen_width(stroke.attrib.get("width"))
            points = _stroke_points(stroke)
            if len(points) >= 2:
                strokes.append((points, width))
        lines.append(strokes)

    inked = sum(len(item) for item in lines)
    chars = len(re.sub(r"\s", "", target))
    if chars and inked < 1:
        raise ValueError("The reply contained no pen strokes.")
    if chars and inked > chars * 20:
        raise ValueError("The reply contained more strokes than the card text can use.")
    _fit_grid(lines)
    return lines


def strokes_to_image(
    lines: list[list[tuple[list[tuple[float, float]], float]]],
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    sx = width / 1000.0
    sy = height / 1000.0
    for line in lines:
        for points, pen in line:
            mapped = [
                (min(width - 1, max(0, x * sx)), min(height - 1, max(0, y * sy)))
                for x, y in points
            ]
            stroke_width = max(2, int(round(pen * ((sx + sy) / 2.0))))
            try:
                draw.line(mapped, fill=INK, width=stroke_width, joint="curve")
            except TypeError:
                draw.line(mapped, fill=INK, width=stroke_width)
    return image


def _request_strokes(
    target: str,
    images: list[tuple[str, str]],
    model: str,
    api_key: str,
    correction: str | None = None,
) -> str:
    instruction = (
        "Write the TARGET below and nothing else. "
        "verbatim and every line text attribute must match it character for character.\n"
        "-----TARGET-----\n"
        f"{target}\n"
        "-----END-----"
    )
    if correction:
        instruction += (
            "\nThe previous reply was rejected because: "
            f"{correction}\nReturn XML only, and do not change the TARGET."
        )
    parts: list[dict] = [{"text": instruction}]
    for mime, encoded in images:
        parts.append({"inline_data": {"mime_type": mime, "data": encoded}})
    configs = (
        {"temperature": 0.2, "maxOutputTokens": 16384, "thinkingConfig": {"thinkingBudget": 4096}},
        {"temperature": 0.2, "maxOutputTokens": 16384},
    )
    last_config_error: Exception | None = None
    for config in configs:
        try:
            return _post(model, api_key, parts, config)
        except _ThinkingRejected as exc:
            last_config_error = exc
            continue
    raise RuntimeError(f"HandwritingAgent request failed: {_redact(str(last_config_error))}")


def _post(model: str, api_key: str, parts: list[dict], generation: dict) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": generation,
    }
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("x-goog-api-key", api_key)
    try:
        with urllib.request.urlopen(request, timeout=100) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _error_detail(exc)
        if exc.code == 400 and "thinking" in detail.lower():
            raise _ThinkingRejected(detail) from exc
        if exc.code in {401, 403}:
            raise RuntimeError("Gemini rejected the API key. Check GEMINI_API_KEY and restart the API.") from exc
        if exc.code == 404:
            raise RuntimeError(
                f"Gemini model {model} is not available to this key. Set GEMINI_MODEL to a model this key can call."
            ) from exc
        raise RuntimeError(f"HandwritingAgent request failed: {_redact(detail)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"HandwritingAgent could not reach Gemini: {_redact(str(exc.reason))}") from exc

    candidates = payload.get("candidates") or []
    if not candidates:
        message = ((payload.get("promptFeedback") or {}).get("blockReason")) or "empty response"
        raise RuntimeError(f"HandwritingAgent returned no writing ({message}).")
    candidate = candidates[0]
    if candidate.get("finishReason") == "MAX_TOKENS":
        raise RuntimeError("HandwritingAgent reply was cut off. Shorten this text block and try again.")
    texts = []
    for part in (candidate.get("content") or {}).get("parts") or []:
        if part.get("thought"):
            continue
        if part.get("text"):
            texts.append(part["text"])
    if not texts:
        raise RuntimeError("HandwritingAgent returned no stroke XML.")
    return "\n".join(texts)


def _prepare_images(blobs: list[bytes]) -> list[tuple[str, str]]:
    prepared: list[tuple[str, str]] = []
    for blob in blobs[-2:]:
        try:
            image = Image.open(io.BytesIO(blob))
            image = image.convert("RGB")
        except Exception:
            continue
        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=85)
        prepared.append(("image/jpeg", base64.b64encode(out.getvalue()).decode("ascii")))
    return prepared


def _cache_path(target: str, images: list[tuple[str, str]], width: int, height: int, model: str) -> Path:
    digest = hashlib.sha256()
    digest.update(model.encode("utf-8"))
    digest.update(target.encode("utf-8"))
    digest.update(f"{width}x{height}".encode("utf-8"))
    for mime, encoded in images:
        digest.update(mime.encode("utf-8"))
        digest.update(encoded.encode("ascii"))
    root = Path(get_settings().storage_dir) / "gemini-cache"
    return root / f"{digest.hexdigest()}.png"


def _extract_xml(payload: str) -> str:
    match = re.search(r"<handwriting\b[^>]*>.*</handwriting>", payload, re.S | re.I)
    if not match:
        raise ValueError("Reply did not contain handwriting XML.")
    return match.group(0)


def _lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if normalized == "":
        return [""]
    return [line.rstrip() for line in normalized.split("\n")]


def _tag(node: ET.Element) -> str:
    return node.tag.rsplit("}", 1)[-1].lower()


def _pen_width(value: str | None) -> float:
    try:
        width = float(value or "4")
    except ValueError:
        width = 4.0
    return min(12.0, max(1.5, width))


def _stroke_points(stroke: ET.Element) -> list[tuple[float, float]]:
    if stroke.attrib.get("d"):
        return _path_points(stroke.attrib["d"])
    points = []
    for node in stroke:
        if _tag(node) != "pt":
            continue
        try:
            points.append((float(node.attrib["x"]), float(node.attrib["y"])))
        except (KeyError, ValueError):
            continue
    return points


def _path_points(path: str) -> list[tuple[float, float]]:
    tokens = [command or number for command, number in re.findall(r"([MLQCZHVmlqczhv])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)", path)]
    points: list[tuple[float, float]] = []
    index = 0
    command = ""
    cx = cy = 0.0

    def take() -> float:
        nonlocal index
        if index >= len(tokens) or _is_command(tokens[index]):
            raise ValueError("A stroke path was incomplete.")
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        if _is_command(tokens[index]):
            command = tokens[index]
            index += 1
            if command in "Zz":
                continue
        if command in "Mm":
            x, y = take(), take()
            if command == "m":
                x += cx
                y += cy
            cx, cy = x, y
            points.append((cx, cy))
            command = "L" if command == "M" else "l"
        elif command in "Ll":
            x, y = take(), take()
            if command == "l":
                x += cx
                y += cy
            cx, cy = x, y
            points.append((cx, cy))
        elif command in "Hh":
            x = take()
            cx = cx + x if command == "h" else x
            points.append((cx, cy))
        elif command in "Vv":
            y = take()
            cy = cy + y if command == "v" else y
            points.append((cx, cy))
        elif command in "Qq":
            x1, y1 = take(), take()
            x, y = take(), take()
            if command == "q":
                x1 += cx
                y1 += cy
                x += cx
                y += cy
            points.extend(_sample_quad((cx, cy), (x1, y1), (x, y)))
            cx, cy = x, y
        elif command in "Cc":
            x1, y1 = take(), take()
            x2, y2 = take(), take()
            x, y = take(), take()
            if command == "c":
                x1 += cx
                y1 += cy
                x2 += cx
                y2 += cy
                x += cx
                y += cy
            points.extend(_sample_cubic((cx, cy), (x1, y1), (x2, y2), (x, y)))
            cx, cy = x, y
        else:
            raise ValueError("A stroke used a path command other than M, L, Q, C, H, or V.")
    return points


def _fit_grid(lines: list[list[tuple[list[tuple[float, float]], float]]]) -> None:
    coords = [value for line in lines for points, _pen in line for point in points for value in point]
    if not coords:
        return
    peak = max(abs(value) for value in coords)
    if peak <= 1.5:
        scale = 1000.0
    elif peak > 1000:
        scale = 1000.0 / peak
    else:
        scale = 1.0
    if scale == 1.0:
        return
    for line in lines:
        for index, (points, pen) in enumerate(line):
            line[index] = ([(x * scale, y * scale) for x, y in points], pen)


def _sample_quad(start, control, end, steps: int = 6) -> list[tuple[float, float]]:
    sampled = []
    for step in range(1, steps + 1):
        t = step / steps
        u = 1 - t
        x = u * u * start[0] + 2 * u * t * control[0] + t * t * end[0]
        y = u * u * start[1] + 2 * u * t * control[1] + t * t * end[1]
        sampled.append((x, y))
    return sampled


def _sample_cubic(start, control_a, control_b, end, steps: int = 6) -> list[tuple[float, float]]:
    sampled = []
    for step in range(1, steps + 1):
        t = step / steps
        u = 1 - t
        x = (u ** 3) * start[0] + 3 * (u ** 2) * t * control_a[0] + 3 * u * (t ** 2) * control_b[0] + (t ** 3) * end[0]
        y = (u ** 3) * start[1] + 3 * (u ** 2) * t * control_a[1] + 3 * u * (t ** 2) * control_b[1] + (t ** 3) * end[1]
        sampled.append((x, y))
    return sampled


def _is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def _error_detail(exc: urllib.error.HTTPError) -> str:
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        message = json.loads(raw).get("error", {}).get("message")
    except json.JSONDecodeError:
        message = None
    return _redact(message or raw or exc.reason or "request failed")


def _redact(message: str) -> str:
    key = get_settings().gemini_api_key.strip()
    if key:
        message = message.replace(key, "[key]")
    return message[:500]


class _ThinkingRejected(Exception):
    pass
