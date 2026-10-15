"""Buttons, icon buttons and a macOS-style segmented control."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QWidget,
)

from ui.theme import icons, theme

_ICON_COLOR = {
    "primary": "#FFFFFF",
    "danger": "#FFFFFF",
}


class Button(QPushButton):
    def __init__(
        self,
        text: str = "",
        *,
        variant: str = "secondary",
        size: str = "md",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._variant = variant
        self._icon_name = icon_name
        self.setProperty("variant", variant)
        self.setProperty("size", size)
        self.setCursor(Qt.PointingHandCursor)
        iconpx = 16 if size != "lg" else 18
        if icon_name:
            color = self._icon_color()
            self.setIcon(icons.icon(icon_name, color, iconpx))
            self.setIconSize(QSize(iconpx, iconpx))

    def _icon_color(self) -> str:
        if self._variant in _ICON_COLOR:
            return _ICON_COLOR[self._variant]
        if self._variant in ("soft",):
            return theme.palette.accent_text
        return theme.palette.text


class IconButton(QToolButton):
    """Square icon-only button, great for toolbars and row actions."""

    def __init__(
        self,
        icon_name: str,
        *,
        tooltip: str = "",
        size: int = 32,
        icon_size: int = 18,
        color: str | None = None,
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._color = color or theme.palette.text_secondary
        self._icon_size = icon_size
        self.setIcon(icons.icon(icon_name, self._color, icon_size))
        self.setIconSize(QSize(icon_size, icon_size))
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(checkable)
        if tooltip:
            self.setToolTip(tooltip)

    def recolor(self, color: str) -> None:
        self._color = color
        self.setIcon(icons.icon(self._icon_name, color, self._icon_size))


class SegmentedControl(QFrame):
    """Exclusive set of options rendered as a single pill, macOS-style."""

    changed = Signal(int)

    def __init__(self, options: list[str], *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Segmented")
        p = theme.palette
        self.setStyleSheet(
            f"""
            QFrame#Segmented {{ background: {p.surface_alt}; border: 1px solid {p.border};
                                border-radius: 2px; }}
            QFrame#Segmented QPushButton {{ background: transparent; border: none;
                                border-radius: 2px; padding: 6px 14px; font-weight: 600;
                                color: {p.text_secondary}; }}
            QFrame#Segmented QPushButton:hover {{ color: {p.text}; }}
            QFrame#Segmented QPushButton:checked {{ background: {p.surface}; color: {p.text};
                                border: 1px solid {p.border}; }}
            """
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(3)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            self._group.addButton(btn, i)
            lay.addWidget(btn)
        self._group.idClicked.connect(self.changed.emit)

    def current_index(self) -> int:
        return self._group.checkedId()

    def set_current(self, index: int) -> None:
        btn = self._group.button(index)
        if btn:
            btn.setChecked(True)
