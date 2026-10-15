"""Loading, empty and error placeholder states."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.theme import icons, theme

from .buttons import Button
from .common import label


class Spinner(QWidget):
    """A smooth rotating arc spinner."""

    def __init__(self, size: int = 28, *, color: str | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self._color = QColor(color or theme.palette.accent)
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def stop(self) -> None:
        self._timer.stop()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        margin = 3
        rect = QRectF(margin, margin, self._size - 2 * margin, self._size - 2 * margin)
        grad = QConicalGradient(rect.center(), -self._angle)
        c = QColor(self._color)
        transparent = QColor(self._color)
        transparent.setAlpha(0)
        grad.setColorAt(0.0, c)
        grad.setColorAt(1.0, transparent)
        pen = QPen(grad, 3)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)
        p.end()


class _Placeholder(QWidget):
    def __init__(self, icon_name: str, title: str, subtitle: str, *,
                 tone: str = "neutral", action: str | None = None,
                 action_variant: str = "primary", action_icon: str | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 48, 40, 48)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignCenter)

        badge = QWidget()
        badge.setFixedSize(64, 64)
        p = theme.palette
        soft = {
            "neutral": p.neutral_soft, "danger": p.danger_soft, "accent": p.accent_soft,
        }.get(tone, p.neutral_soft)
        fg = {
            "neutral": p.text_muted, "danger": p.danger, "accent": p.accent,
        }.get(tone, p.text_muted)
        badge.setStyleSheet(f"background: {soft}; border-radius: 2px;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, fg, 30))
        ic.setAlignment(Qt.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge, alignment=Qt.AlignCenter)

        t = label(title, "subtitle")
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        lay.addWidget(t)

        s = label(subtitle, "secondary")
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setMaximumWidth(380)
        lay.addWidget(s, alignment=Qt.AlignCenter)

        self.action_button: Button | None = None
        if action:
            btn = Button(action, variant=action_variant, icon_name=action_icon)
            self.action_button = btn
            lay.addSpacing(6)
            lay.addWidget(btn, alignment=Qt.AlignCenter)


class EmptyState(_Placeholder):
    def __init__(self, title: str, subtitle: str, *, icon_name: str = "documents",
                 action: str | None = None, action_icon: str | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(icon_name, title, subtitle, tone="neutral",
                         action=action, action_icon=action_icon, parent=parent)


class ErrorState(_Placeholder):
    def __init__(self, title: str = "Something went wrong",
                 subtitle: str = "We couldn't load this content. Please try again.",
                 *, action: str | None = "Retry", parent: QWidget | None = None) -> None:
        super().__init__("warning", title, subtitle, tone="danger",
                         action=action, action_variant="secondary",
                         action_icon="refresh", parent=parent)


class LoadingState(QWidget):
    def __init__(self, text: str = "Loading…", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 60, 40, 60)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignCenter)
        self._spinner = Spinner(34)
        lay.addWidget(self._spinner, alignment=Qt.AlignCenter)
        lbl = label(text, "secondary")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl, alignment=Qt.AlignCenter)

    def stop(self) -> None:
        self._spinner.stop()
