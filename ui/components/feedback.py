"""Toast notifications.

A :class:`ToastHost` overlays the main window and stacks transient messages in
the bottom-right corner.  Call :meth:`ToastHost.show_toast` from anywhere that
has a reference to the host (the main window exposes ``self.toasts``).
"""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ui.theme import card_shadow, icons, theme

from .buttons import IconButton
from .common import label

_TONE = {
    "success": ("check-circle", "success", "success_soft"),
    "error": ("error", "danger", "danger_soft"),
    "warning": ("warning", "warning", "warning_soft"),
    "info": ("info", "info", "info_soft"),
}


class Toast(QFrame):
    def __init__(self, message: str, tone: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        icon_name, fg_attr, soft_attr = _TONE.get(tone, _TONE["info"])
        p = theme.palette
        self.setObjectName("Toast")
        self.setStyleSheet(
            f"QFrame#Toast {{ background: {p.surface}; border: 1px solid {p.border};"
            f" border-radius: 2px; }}")
        self.setGraphicsEffect(card_shadow(blur=30, y=8, alpha=46))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 10, 12)
        lay.setSpacing(10)

        dot = QFrame()
        dot.setFixedSize(26, 26)
        dot.setStyleSheet(f"background: {getattr(p, soft_attr)}; border-radius: 2px;")
        dl = QVBoxLayout(dot)
        dl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, getattr(p, fg_attr), 16))
        ic.setAlignment(Qt.AlignCenter)
        dl.addWidget(ic)
        lay.addWidget(dot)

        msg = label(message, "body")
        msg.setWordWrap(False)
        msg.setStyleSheet("font-weight: 600;")
        lay.addWidget(msg)
        lay.addSpacing(6)

        close = IconButton("close", size=26, icon_size=14, color=p.text_muted)
        close.clicked.connect(self._dismiss)
        lay.addWidget(close)

        self._opacity = QGraphicsOpacityEffect(self)
        # NB: a widget can only hold one graphics effect; shadow stays, so we animate
        # geometry/position via the parent instead of opacity here.
        self.setMinimumWidth(260)

    def _dismiss(self) -> None:
        host = self.parent()
        if isinstance(host, ToastHost):
            host.remove_toast(self)


class ToastHost(QWidget):
    """Stacks toasts in the bottom-right of its parent.

    Crucially, this overlay is only ever sized to the toast stack itself (and is
    zero-sized when empty) so it never covers — and therefore never swallows
    clicks destined for — the rest of the UI.
    """

    _MARGIN = 20
    _GAP = 10

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._toasts: list[Toast] = []
        parent.installEventFilter(self)
        self.setGeometry(0, 0, 0, 0)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self._reposition()
        return False

    def show_toast(self, message: str, tone: str = "info", *, duration: int = 3200) -> None:
        toast = Toast(message, tone, parent=self)
        self._toasts.append(toast)
        toast.show()
        toast.adjustSize()
        self._reposition()
        self._animate_in(toast)
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.remove_toast(toast))

    def _animate_in(self, toast: Toast) -> None:
        end = toast.pos()
        start = QPoint(end.x() + 30, end.y())
        anim = QPropertyAnimation(toast, b"pos", toast)
        anim.setDuration(200)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def remove_toast(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            toast.deleteLater()
            self._reposition()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        if not self._toasts:
            self.setGeometry(0, 0, 0, 0)
            return
        width = 0
        total = 0
        for toast in self._toasts:
            toast.adjustSize()
            width = max(width, toast.width())
            total += toast.height() + self._GAP
        total -= self._GAP
        x = parent.width() - width - self._MARGIN
        y = parent.height() - total - self._MARGIN
        self.setGeometry(x, y, width, total)
        cy = 0
        for toast in self._toasts:
            toast.move(width - toast.width(), cy)
            cy += toast.height() + self._GAP
        self.raise_()
