"""Collapsible left navigation rail."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.components import label
from ui.theme import icons, theme

# (key, label, icon)
NAV_ITEMS = [
    ("dashboard", "Dashboard", "dashboard"),
    ("documents", "Documents", "documents"),
    ("templates", "Templates", "templates"),
    ("handwriting", "Handwriting", "handwriting"),
    ("batch", "Batch Generator", "batch"),
    ("exports", "Exports", "exports"),
]

BOTTOM_ITEMS = [
    ("settings", "Settings", "settings"),
]

EXPANDED_W = 232
COLLAPSED_W = 64


class NavItem(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, text: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._key = key
        self._icon_name = icon_name
        self._text = text
        self._active = False
        self._collapsed = False
        self.setObjectName("NavItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)

        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(14, 0, 12, 0)
        self._lay.setSpacing(12)
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        self._lay.addWidget(self._icon)
        self._label = label(text, "body")
        self._label.setWordWrap(False)
        self._lay.addWidget(self._label)
        self._lay.addStretch(1)
        self._restyle()

    def _restyle(self) -> None:
        p = theme.palette
        if self._active:
            self.setStyleSheet(
                f"QFrame#NavItem {{ background: {p.accent_soft}; border-radius: 2px; }}")
            self._icon.setPixmap(icons.pixmap(self._icon_name, p.accent, 20))
            self._label.setStyleSheet(f"color: {p.accent_text}; font-weight: 600; background: transparent;")
        else:
            self.setStyleSheet(
                "QFrame#NavItem { background: transparent; border-radius: 2px; }"
                f"QFrame#NavItem:hover {{ background: {p.control_hover}; }}")
            self._icon.setPixmap(icons.pixmap(self._icon_name, p.text_secondary, 20))
            self._label.setStyleSheet(f"color: {p.text_secondary}; background: transparent;")

    def set_active(self, active: bool) -> None:
        self._active = active
        self._restyle()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._label.setVisible(not collapsed)
        if collapsed:
            self._lay.setContentsMargins(0, 0, 0, 0)
            self._lay.setAlignment(Qt.AlignCenter)
            self._icon.setAlignment(Qt.AlignCenter)
            self.setToolTip(self._text)
        else:
            self._lay.setContentsMargins(14, 0, 12, 0)
            self._lay.setAlignment(Qt.Alignment())
            self.setToolTip("")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._key)


class Sidebar(QFrame):
    navigate = Signal(str)
    toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._collapsed = False
        self._items: dict[str, NavItem] = {}
        self.setFixedWidth(EXPANDED_W)
        self._apply_bg()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 14)
        root.setSpacing(4)

        # --- brand ---
        self._brand = self._build_brand()
        root.addWidget(self._brand)
        root.addSpacing(14)

        for key, text, icon_name in NAV_ITEMS:
            item = NavItem(key, text, icon_name)
            item.clicked.connect(self.navigate.emit)
            self._items[key] = item
            root.addWidget(item)

        root.addStretch(1)

        for key, text, icon_name in BOTTOM_ITEMS:
            item = NavItem(key, text, icon_name)
            item.clicked.connect(self.navigate.emit)
            self._items[key] = item
            root.addWidget(item)

        root.addSpacing(8)
        self._footer = self._build_footer()
        root.addWidget(self._footer)

    def _apply_bg(self) -> None:
        p = theme.palette
        self.setStyleSheet(
            f"QFrame#Sidebar {{ background: {p.sidebar}; border-right: 1px solid {p.border}; }}")

    def _build_brand(self) -> QWidget:
        p = theme.palette
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 0, 0, 0)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setFixedSize(30, 30)
        logo.setPixmap(icons.pixmap("handwriting", "#FFFFFF", 18))
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"background: {p.accent}; border-radius: 2px;")
        lay.addWidget(logo)
        self._brand_text = QWidget()
        tl = QVBoxLayout(self._brand_text)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)
        name = label("HandScript", "body")
        name.setWordWrap(False)
        name.setStyleSheet("font-weight: 700; font-size: 14px;")
        tl.addWidget(name)
        studio = label("Studio", "muted")
        studio.setWordWrap(False)
        tl.addWidget(studio)
        lay.addWidget(self._brand_text)
        lay.addStretch(1)
        return w

    def _build_footer(self) -> QWidget:
        p = theme.palette
        self._footer_card = QFrame()
        self._footer_card.setObjectName("Footer")
        self._footer_card.setStyleSheet(
            f"QFrame#Footer {{ background: {p.surface}; border: 1px solid {p.border};"
            f" border-radius: 2px; }}")
        lay = QVBoxLayout(self._footer_card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {p.success}; border-radius: 2px;")
        row.addWidget(dot)
        ws = label("Local workspace", "caption")
        ws.setWordWrap(False)
        ws.setStyleSheet("font-weight: 600;")
        row.addWidget(ws)
        row.addStretch(1)
        lay.addLayout(row)
        path = label("~/HandScript", "caption")
        path.setWordWrap(False)
        lay.addWidget(path)
        ver = label("v0.9.0 · Help & shortcuts", "caption")
        ver.setWordWrap(False)
        ver.setCursor(Qt.PointingHandCursor)
        lay.addWidget(ver)
        return self._footer_card

    def set_active(self, key: str) -> None:
        for k, item in self._items.items():
            item.set_active(k == key)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.setFixedWidth(COLLAPSED_W if collapsed else EXPANDED_W)
        self._brand_text.setVisible(not collapsed)
        self._footer_card.setVisible(not collapsed)
        for item in self._items.values():
            item.set_collapsed(collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed
