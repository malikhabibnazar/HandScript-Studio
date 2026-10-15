"""Theme package: tokens, stylesheet builder and icon system."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from . import icons
from .qss import build_qss
from .tokens import DARK, LIGHT, RADIUS, SPACING, Palette, Theme, Typography, theme

__all__ = [
    "icons",
    "build_qss",
    "apply_theme",
    "card_shadow",
    "DARK",
    "LIGHT",
    "RADIUS",
    "SPACING",
    "Palette",
    "Theme",
    "Typography",
    "theme",
]


def apply_theme(app: QApplication, mode: str | None = None) -> None:
    """Apply (or re-apply) the global stylesheet to the whole application."""
    if mode is not None:
        theme.set_mode(mode)
    app.setStyleSheet(build_qss(theme.palette, theme.type))


def card_shadow(blur: int = 24, y: int = 6, alpha: int = 28):
    """Shadows are intentionally disabled — the design uses flat, bordered
    surfaces instead. Returning ``None`` clears any effect on the widget."""
    return None
