"""Talk to the HandFonted container. This process never imports Paddle."""
from __future__ import annotations

import base64
from pathlib import Path

import httpx

from app.config import get_settings


class HandfontedError(RuntimeError):
    pass


def handfonted_status() -> dict:
    url = _url()
    try:
        response = httpx.get(f"{url}/health", timeout=2.0)
        body = response.json() if response.content else {}
    except Exception:
        return {
            "ready": False,
            "url": url,
            "message": "The HandFonted container is not running.",
        }
    ready = response.status_code == 200 and bool(body.get("ready"))
    return {
        "ready": ready,
        "url": url,
        "message": str(body.get("message") or ("HandFonted is ready." if ready else "HandFonted is still loading its models.")),
    }


def process_image(raw: bytes, filename: str) -> list[dict]:
    """Return glyphs as label, confidence, and PNG bytes."""
    try:
        response = httpx.post(
            f"{_url()}/v1/process",
            files={"image": (filename or "handwriting.png", raw, "application/octet-stream")},
            timeout=180.0,
        )
    except httpx.HTTPError as exc:
        raise HandfontedError("The HandFonted container is not running.") from exc
    _raise_for_status(response)
    characters = response.json().get("characters") or []
    glyphs = []
    for item in characters:
        encoded = item.get("image_png_base64") or ""
        if not encoded:
            continue
        glyphs.append({
            "label": str(item.get("label") or "")[:1],
            "confidence": float(item.get("confidence") or 0),
            "png": base64.b64decode(encoded),
        })
    if not glyphs:
        raise HandfontedError("No characters were found in that photo.")
    return glyphs


def build_font(glyphs: list[dict], dest: Path, *, font_name: str, thickness: int) -> None:
    payload = {
        "font_name": font_name or "My Handwriting",
        "thickness": int(thickness),
        "characters": [
            {
                "label": item["label"],
                "image_png_base64": base64.b64encode(item["png"]).decode("ascii"),
            }
            for item in glyphs
            if item.get("label") and item.get("png")
        ],
    }
    try:
        response = httpx.post(f"{_url()}/v1/font", json=payload, timeout=180.0)
    except httpx.HTTPError as exc:
        raise HandfontedError("The HandFonted container is not running.") from exc
    _raise_for_status(response)
    if len(response.content) < 64:
        raise HandfontedError("HandFonted did not return a font file.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)


def _url() -> str:
    return get_settings().handfonted_url.rstrip("/")


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    detail = ""
    try:
        body = response.json()
        detail = body.get("detail") if isinstance(body, dict) else ""
    except Exception:
        detail = response.text[:240]
    if response.status_code == 503:
        raise HandfontedError(detail or "HandFonted is still loading its models.")
    raise HandfontedError(detail or "HandFonted could not finish that step.")
