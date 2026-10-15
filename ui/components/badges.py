"""Status pills and tonal badges."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ui.theme import theme

from .common import label

# tone -> (fg_attr, soft_attr)
_TONES = {
    "success": ("success", "success_soft"),
    "warning": ("warning", "warning_soft"),
    "danger": ("danger", "danger_soft"),
    "info": ("info", "info_soft"),
    "accent": ("accent_text", "accent_soft"),
    "neutral": ("neutral", "neutral_soft"),
}

# status string -> (tone, animated?)
STATUS_TONES = {
    # documents
    "Draft": ("neutral", False),
    "Ready": ("info", False),
    "Generating": ("warning", True),
    "Completed": ("success", False),
    "Failed": ("danger", False),
    # profiles
    "Processing": ("warning", True),
    "Needs Review": ("warning", False),
    "Error": ("danger", False),
    # templates
    "Published": ("success", False),
    # batches / exports
    "Running": ("warning", True),
    "Queued": ("neutral", False),
    "Paused": ("neutral", False),
    "Cancelled": ("neutral", False),
    "Partial": ("warning", False),
}


def tone_for(status: str) -> str:
    return STATUS_TONES.get(status, ("neutral", False))[0]


class Badge(QWidget):
    """A pill with optional leading dot."""

    def __init__(self, text: str, tone: str = "neutral", *, dot: bool = True,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        fg_attr, soft_attr = _TONES.get(tone, _TONES["neutral"])
        self._fg = QColor(getattr(theme.palette, fg_attr))
        self._soft = QColor(getattr(theme.palette, soft_attr))
        self._dot = dot
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 11, 4)
        lay.setSpacing(6)
        if dot:
            lay.addSpacing(10)  # room for painted dot
        self._label = label(text, "body")
        self._label.setWordWrap(False)
        self._label.setStyleSheet(
            f"color: {self._fg.name()}; font-size: 12px; font-weight: 600; background: transparent;")
        lay.addWidget(self._label)
        self.setMaximumHeight(26)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(self._soft)
        p.drawRoundedRect(self.rect(), 2, 2)
        if self._dot:
            p.setBrush(self._fg)
            cy = self.height() // 2
            p.drawRoundedRect(11, cy - 3, 6, 6, 1, 1)
        p.end()


def status_badge(status: str, *, parent: QWidget | None = None) -> Badge:
    tone = tone_for(status)
    return Badge(status, tone, parent=parent)


class CountPill(QWidget):
    """A compact neutral pill showing a number, e.g. a filter count."""

    def __init__(self, text: str, *, tone: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        fg_attr, soft_attr = _TONES.get(tone, _TONES["neutral"])
        p = theme.palette
        self.setStyleSheet(
            f"background: {getattr(p, soft_attr)}; border-radius: 2px;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 1, 8, 1)
        lbl = label(text, "caption")
        lbl.setStyleSheet(
            f"color: {getattr(p, fg_attr)}; font-weight: 700; font-size: 11px; background: transparent;")
        lbl.setWordWrap(False)
        lay.addWidget(lbl)
        self.setMaximumHeight(20)
