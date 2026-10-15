"""Higher-level cards: metric cards, quick-action tiles, list rows."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ui.theme import icons, theme

from .common import Card, label


class StatCard(Card):
    """A dashboard overview metric: icon, big number, label and optional delta."""

    def __init__(self, title: str, value: str, icon_name: str, *,
                 tone: str = "accent", delta: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent, padding=18, spacing=12)
        p = theme.palette
        soft = {
            "accent": p.accent_soft, "success": p.success_soft,
            "warning": p.warning_soft, "neutral": p.neutral_soft,
        }.get(tone, p.accent_soft)
        fg = {
            "accent": p.accent, "success": p.success,
            "warning": p.warning, "neutral": p.text_secondary,
        }.get(tone, p.accent)

        top = QHBoxLayout()
        top.setSpacing(10)
        badge = QFrame()
        badge.setFixedSize(38, 38)
        badge.setStyleSheet(f"background: {soft}; border-radius: 2px;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, fg, 20))
        ic.setAlignment(Qt.AlignCenter)
        bl.addWidget(ic)
        top.addWidget(badge)
        top.addStretch(1)
        if delta:
            d = label(delta, "caption")
            d.setStyleSheet(f"color: {p.success}; font-weight: 600;")
            d.setWordWrap(False)
            top.addWidget(d, alignment=Qt.AlignTop)
        self.add_layout(top)

        value_lbl = label(value, "metric")
        value_lbl.setWordWrap(False)
        self.add(value_lbl)
        title_lbl = label(title, "secondary")
        title_lbl.setWordWrap(False)
        self.add(title_lbl)


class QuickActionTile(QFrame):
    """A clickable tile with icon, title and subtitle."""

    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon_name: str, *,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuickTile")
        self.setCursor(Qt.PointingHandCursor)
        p = theme.palette
        self._base = (f"QFrame#QuickTile {{ background: {p.surface}; border: 1px solid {p.border};"
                      f" border-radius: 2px; }}")
        self._hover = (f"QFrame#QuickTile {{ background: {p.surface}; border: 1px solid {p.accent};"
                       f" border-radius: 2px; }}")
        self.setStyleSheet(self._base)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 13, 14, 13)
        lay.setSpacing(12)

        badge = QFrame()
        badge.setFixedSize(36, 36)
        badge.setStyleSheet(f"background: {p.accent_soft}; border-radius: 2px;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, p.accent, 19))
        ic.setAlignment(Qt.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge)

        col = QVBoxLayout()
        col.setSpacing(1)
        t = label(title, "body")
        t.setStyleSheet("font-weight: 600;")
        t.setWordWrap(False)
        col.addWidget(t)
        s = label(subtitle, "muted")
        s.setWordWrap(False)
        col.addWidget(s)
        lay.addLayout(col)
        lay.addStretch(1)

        chev = label("")
        chev.setPixmap(icons.pixmap("chevron-right", p.text_muted, 16))
        lay.addWidget(chev)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(self._hover)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(self._base)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class StatusRow(QWidget):
    """A single system-status line: label + colored state + optional detail."""

    def __init__(self, title: str, state: str, tone: str = "success", *,
                 detail: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        p = theme.palette
        fg = {"success": p.success, "warning": p.warning, "danger": p.danger,
              "neutral": p.text_muted}.get(tone, p.success)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {fg}; border-radius: 2px;")
        lay.addWidget(dot)
        t = label(title, "body")
        t.setWordWrap(False)
        lay.addWidget(t)
        lay.addStretch(1)
        if detail:
            lay.addWidget(label(detail, "muted"))
        state_lbl = label(state, "body")
        state_lbl.setWordWrap(False)
        state_lbl.setStyleSheet(f"color: {fg}; font-weight: 600;")
        lay.addWidget(state_lbl)
