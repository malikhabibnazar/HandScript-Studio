"""Horizontal numbered step indicator for multi-step flows."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ui.theme import theme


class Stepper(QWidget):
    def __init__(self, steps: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps = steps
        self._current = 0
        self.setFixedHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_current(self, index: int) -> None:
        self._current = max(0, min(index, len(self._steps) - 1))
        self.update()

    def current(self) -> int:
        return self._current

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        n = len(self._steps)
        if n == 0:
            return
        radius = 14
        top = 6
        cy = top + radius
        inset = 56
        left = inset
        right = self.width() - inset
        span = right - left if n > 1 else 0
        centers = [left + (span * i / (n - 1)) if n > 1 else left for i in range(n)]

        # connectors
        for i in range(n - 1):
            done = i < self._current
            pen = QPen(QColor(p.accent if done else p.border), 2)
            painter.setPen(pen)
            x1 = centers[i] + radius + 4
            x2 = centers[i + 1] - radius - 4
            painter.drawLine(int(x1), cy, int(x2), cy)

        f = QFont(theme.type.family)
        f.setPixelSize(12)
        f.setWeight(QFont.DemiBold)

        for i, step in enumerate(self._steps):
            cx = centers[i]
            circle = QRectF(cx - radius, top, radius * 2, radius * 2)
            if i < self._current:  # completed
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(p.accent))
                painter.drawRoundedRect(circle, 2, 2)
                painter.setPen(QPen(QColor("#FFFFFF"), 2))
                painter.drawLine(int(cx - 4), int(cy), int(cx - 1), int(cy + 3))
                painter.drawLine(int(cx - 1), int(cy + 3), int(cx + 5), int(cy - 4))
            elif i == self._current:  # current
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(p.accent))
                painter.drawRoundedRect(circle, 2, 2)
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(f)
                painter.drawText(circle, Qt.AlignCenter, str(i + 1))
            else:  # upcoming
                painter.setBrush(QColor(p.surface))
                painter.setPen(QPen(QColor(p.border_strong), 1.5))
                painter.drawRoundedRect(circle, 2, 2)
                painter.setPen(QColor(p.text_muted))
                painter.setFont(f)
                painter.drawText(circle, Qt.AlignCenter, str(i + 1))

            # label
            lf = QFont(theme.type.family)
            lf.setPixelSize(12)
            is_active = i <= self._current
            lf.setWeight(QFont.DemiBold if i == self._current else QFont.Normal)
            painter.setFont(lf)
            painter.setPen(QColor(p.text if is_active else p.text_muted))
            label_rect = QRectF(cx - 56, top + radius * 2 + 6, 112, 18)
            painter.drawText(label_rect, Qt.AlignCenter, step)

        painter.end()
