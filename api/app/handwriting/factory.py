"""Choose a handwriting engine.

The process default comes from configuration and is what tests and profiles
without an explicit choice use. A profile can ask for Graves or Handwrite on
its own. A missing Graves weight file falls back to the script font.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.handwriting.base import HandwritingEngine
from app.handwriting.font_engine import FontEngine
from app.handwriting.handwrite_engine import handwrite_status
from app.handwriting.pillow_engine import face_catalog

log = logging.getLogger(__name__)

_engine: HandwritingEngine | None = None
_named: dict[str, HandwritingEngine] = {}
_detail = {"requested": "font", "active": "font", "weights_loaded": False, "message": "Script font"}


def engine_status() -> dict:
    get_handwriting_engine()
    settings = get_settings()
    status = dict(_detail)
    status["default_style_id"] = settings.graves_default_style_id
    styles = Path(settings.graves_styles_dir)
    ids = []
    if styles.exists():
        for path in styles.glob("style-*-strokes.npy"):
            piece = path.name.split("-")[1]
            if piece.isdigit():
                ids.append(int(piece))
    status["style_ids"] = sorted(ids)
    status["handwrite"] = handwrite_status()
    status["faces"] = face_catalog()
    from app.handwriting.sheet_engine import sheet_status

    status["sheets"] = sheet_status()
    status["gemini"] = {
        "configured": bool(settings.gemini_api_key.strip()),
        "model": settings.gemini_model,
    }
    from app.handwriting.onedm_engine import onedm_status

    status["onedm"] = onedm_status()
    from app.handwriting.drawfont_engine import drawfont_status

    status["drawfont"] = drawfont_status()
    from app.handwriting.handfonted_client import handfonted_status

    status["handfonted"] = handfonted_status()
    return status


def get_handwriting_engine(
    name: str | None = None,
    *,
    font_path: str | None = None,
    font_family: str | None = None,
) -> HandwritingEngine:
    if name:
        return _for_profile(name, font_path, font_family)
    global _engine
    if _engine is None:
        _engine = _build()
    return _engine


def reset_handwriting_engine() -> None:
    global _engine
    _engine = None
    _named.clear()


def _for_profile(name: str, font_path: str | None, font_family: str | None = None) -> HandwritingEngine:
    key = name.strip().lower()
    if key == "handwrite":
        cache = f"handwrite:{font_path or ''}"
        if cache not in _named:
            from app.handwriting.handwrite_engine import HandwriteEngine

            _named[cache] = HandwriteEngine(font_path)
        return _named[cache]
    if key == "pillow":
        cache = f"pillow:{font_family or 'caveat'}"
        if cache not in _named:
            from app.handwriting.pillow_engine import PillowEngine

            _named[cache] = PillowEngine(font_family)
        return _named[cache]
    if key in {"hw2font", "fontmaker", "drawfont", "handfonted"}:
        cache = f"{key}:{font_path or ''}"
        if cache not in _named:
            from app.handwriting.sheet_engine import SheetEngine

            _named[cache] = SheetEngine(key, font_path)
        return _named[cache]
    if key == "gemini":
        if "gemini" not in _named:
            from app.handwriting.gemini_engine import GeminiEngine

            _named["gemini"] = GeminiEngine()
        return _named["gemini"]
    if key == "onedm":
        if "onedm" not in _named:
            from app.handwriting.onedm_engine import OneDMEngine

            _named["onedm"] = OneDMEngine()
        return _named["onedm"]
    if key == "graves":
        if "graves" not in _named:
            loaded, _message = _load_graves()
            _named["graves"] = loaded if loaded is not None else FontEngine()
        return _named["graves"]
    return get_handwriting_engine(font_family=font_family)


def _load_graves() -> tuple[HandwritingEngine | None, str]:
    settings = get_settings()
    if not settings.graves_enabled:
        return None, "Graves is turned off. Using the script font."
    path = Path(settings.graves_weights_path)
    if not path.exists():
        message = f"Graves weights were not found at {path}. Using the script font."
        log.warning(message)
        return None, message
    try:
        from app.handwriting.graves.engine import GravesEngine

        engine = GravesEngine(path, Path(settings.graves_styles_dir))
    except Exception as exc:
        message = f"Graves failed to load ({exc}). Using the script font."
        log.warning(message)
        return None, message
    log.info("Handwriting engine: Graves (%s)", path)
    return engine, "Local Graves LSTM. Styles are built-in primers, not clones of uploaded samples."


def _build() -> HandwritingEngine:
    global _detail
    settings = get_settings()
    requested = (settings.handwriting_engine or "font").strip().lower()
    if requested == "onedm":
        from app.handwriting.onedm_engine import OneDMEngine, onedm_status

        info = onedm_status()
        _detail = {
            "requested": "onedm",
            "active": "onedm",
            "weights_loaded": info.get("weights_loaded", False),
            "message": info.get("message", "One-DM Diffusion Engine"),
        }
        return OneDMEngine()
    if requested != "graves":
        _detail = {
            "requested": requested,
            "active": "font",
            "weights_loaded": False,
            "message": "Script-font renderer.",
        }
        log.info("Handwriting engine: script font (%s)", requested)
        return FontEngine()
    engine, message = _load_graves()
    if engine is None:
        _detail = {
            "requested": "graves",
            "active": "font",
            "weights_loaded": False,
            "message": message,
        }
        return FontEngine()
    _detail = {
        "requested": "graves",
        "active": "graves",
        "weights_loaded": True,
        "message": message,
    }
    return engine
