"""Page header, breadcrumb and section header components."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ui.theme import icons, theme

from .common import label


class Breadcrumb(QWidget):
    """Clickable breadcrumb trail. Emits the index of a clicked crumb."""

    navigate = Signal(int)

    def __init__(self, crumbs: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(6)
        self.set_crumbs(crumbs)

    def set_crumbs(self, crumbs: list[str]) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        last = len(crumbs) - 1
        for i, crumb in enumerate(crumbs):
            lbl = label(crumb, "muted" if i < last else "secondary")
            lbl.setWordWrap(False)
            if i < last:
                lbl.setCursor(Qt.PointingHandCursor)
                lbl.mousePressEvent = lambda e, idx=i: self.navigate.emit(idx)  # type: ignore
            else:
                lbl.setStyleSheet(f"color: {theme.palette.text}; font-weight: 600;")
            self._lay.addWidget(lbl)
            if i < last:
                sep = label("")
                sep.setPixmap(icons.pixmap("chevron-right", theme.palette.text_muted, 14))
                self._lay.addWidget(sep)
        self._lay.addStretch(1)


class PageHeader(QWidget):
    """Standard page header: optional breadcrumb, title, subtitle and actions.

    Action buttons added via :meth:`add_action` appear right-aligned.
    """

    def __init__(self, title: str, subtitle: str = "", *,
                 breadcrumb: list[str] | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.breadcrumb: Breadcrumb | None = None
        if breadcrumb:
            self.breadcrumb = Breadcrumb(breadcrumb)
            root.addWidget(self.breadcrumb)

        row = QHBoxLayout()
        row.setSpacing(16)
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self._title = label(title, "title")
        self._title.setWordWrap(False)
        text_col.addWidget(self._title)
        self._subtitle = label(subtitle, "secondary")
        self._subtitle.setVisible(bool(subtitle))
        text_col.addWidget(self._subtitle)
        row.addLayout(text_col, stretch=1)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(10)
        self._actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addLayout(self._actions)
        root.addLayout(row)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))

    def add_action(self, widget: QWidget) -> QWidget:
        self._actions.addWidget(widget)
        return widget


class SectionHeader(QWidget):
    """A small section title with an optional trailing action/widget."""

    def __init__(self, title: str, *, trailing: QWidget | None = None,
                 subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = label(title, "subtitle")
        t.setWordWrap(False)
        col.addWidget(t)
        if subtitle:
            sub = label(subtitle, "muted")
            sub.setWordWrap(False)
            col.addWidget(sub)
        lay.addLayout(col, stretch=1)
        if trailing is not None:
            lay.addWidget(trailing)
