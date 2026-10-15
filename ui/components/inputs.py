"""Form controls: search field, labeled field wrapper, select, toggle switch."""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QStyle,
    QStyleOptionComboBox,
    QVBoxLayout,
    QWidget,
)

from ui.theme import icons, theme

from .common import label


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Search…", *, width: int | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        act = self.addAction(
            icons.icon("search", theme.palette.text_muted, 16),
            QLineEdit.LeadingPosition,
        )
        act.setEnabled(False)
        if width:
            self.setFixedWidth(width)
        self.setMinimumHeight(34)


class Select(QComboBox):
    """QComboBox that paints a crisp chevron on the right."""

    def __init__(self, items: list[str] | None = None, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if items:
            self.addItems(items)
        self.setMinimumHeight(34)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        self.style().drawComplexControl(QStyle.CC_ComboBox, opt, painter, self)
        self.style().drawControl(QStyle.CE_ComboBoxLabel, opt, painter, self)
        pm = icons.pixmap("chevron-down", theme.palette.text_muted, 16)
        x = self.width() - 22
        y = (self.height() - 16) // 2
        painter.drawPixmap(x, y, pm)
        painter.end()


class Field(QWidget):
    """Vertical label + control, with optional helper text below."""

    def __init__(self, label_text: str, control: QWidget, *, help_text: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        cap = label(label_text, "secondary")
        cap.setWordWrap(False)
        lay.addWidget(cap)
        lay.addWidget(control)
        if help_text:
            lay.addWidget(label(help_text, "caption"))
        self.control = control


class ToggleSwitch(QCheckBox):
    """An animated iOS/macOS-style toggle."""

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def hitButton(self, pos) -> bool:  # noqa: N802
        return self.contentsRect().contains(pos)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        track_on = QColor(p.accent)
        track_off = QColor(p.border_strong)
        track = QColor(track_on if self._offset > 0.5 else track_off)
        # blend
        r = int(track_off.red() + (track_on.red() - track_off.red()) * self._offset)
        g = int(track_off.green() + (track_on.green() - track_off.green()) * self._offset)
        b = int(track_off.blue() + (track_on.blue() - track_off.blue()) * self._offset)
        track = QColor(r, g, b)
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 2, 2)
        knob_d = self.height() - 6
        x = 3 + self._offset * (self.width() - knob_d - 6)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(int(x), 3, knob_d, knob_d, 2, 2)
        painter.end()


class FilterChip(QWidget):
    """A small toggleable filter pill with a count — used in list filters."""

    toggled = Signal(bool)

    def __init__(self, text: str, *, active: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active = active
        self._text = text
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        self._label = label(text, "secondary")
        self._label.setWordWrap(False)
        lay.addWidget(self._label)
        self._restyle()

    def _restyle(self) -> None:
        p = theme.palette
        if self._active:
            self.setStyleSheet(
                f"background: {p.accent_soft}; border: 1px solid {p.accent}; border-radius: 2px;")
            self._label.setStyleSheet(f"color: {p.accent_text}; font-weight: 600;")
        else:
            self.setStyleSheet(
                f"background: {p.surface}; border: 1px solid {p.border}; border-radius: 2px;")
            self._label.setStyleSheet(f"color: {p.text_secondary};")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._active = not self._active
        self._restyle()
        self.toggled.emit(self._active)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._label.sizeHint().width() + 28, 30)
