"""HandScript Studio — application entry point.

Frontend-only build: every page is driven by in-memory mock services so the
whole application is navigable without a database, network or the future
rendering engine.
"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from services.registry import build_services
from ui.main_window import MainWindow
from ui.theme import apply_theme, theme


def _first_available(candidates: list[str], fallback: str) -> str:
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return fallback


def _resolve_fonts() -> None:
    """Pick the best native UI / mono / handwriting fonts for this platform."""
    ui = _first_available(
        ["SF Pro Text", ".AppleSystemUIFont", "Helvetica Neue", "Segoe UI Variable Display",
         "Segoe UI", "Inter", "Roboto"],
        "Segoe UI",
    )
    mono = _first_available(
        ["SF Mono", "JetBrains Mono", "Cascadia Code", "Consolas", "Menlo", "DejaVu Sans Mono"],
        "Consolas",
    )
    hand = _first_available(
        ["Snell Roundhand", "Bradley Hand", "Segoe Script", "Comic Sans MS",
         "Brush Script MT", "Apple Chancery"],
        "Segoe Script",
    )
    theme.type.family = ui
    theme.type.mono = mono
    theme.type.handwriting = hand


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("HandScript Studio")
    app.setOrganizationName("HandScript")
    app.setApplicationDisplayName("HandScript Studio")

    _resolve_fonts()
    base_font = QFont(theme.type.family)
    base_font.setPixelSize(13)
    app.setFont(base_font)

    apply_theme(app, "light")

    services = build_services()
    window = MainWindow(services)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
