"""A styled table built on QTableWidget with sensible desktop defaults."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ui.theme import icons, theme


class DataTable(QTableWidget):
    def __init__(self, headers: list[str], *, parent: QWidget | None = None) -> None:
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.verticalHeader().setDefaultSectionSize(52)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setFixedHeight(40)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def set_stretch(self, columns: dict[int, QHeaderView.ResizeMode]) -> None:
        header = self.horizontalHeader()
        for col in range(self.columnCount()):
            mode = columns.get(col, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(col, mode)

    def add_row(self, values: list) -> int:
        row = self.rowCount()
        self.insertRow(row)
        for col, value in enumerate(values):
            if isinstance(value, QWidget):
                self.set_cell_widget(row, col, value)
            else:
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.setItem(row, col, item)
        return row

    def set_cell_widget(self, row: int, col: int, widget: QWidget) -> None:
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)
        lay.addWidget(widget)
        lay.addStretch(1)
        self.setCellWidget(row, col, wrap)

    def set_actions_widget(self, row: int, col: int, widget: QWidget) -> None:
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(6, 0, 10, 0)
        lay.setSpacing(2)
        lay.addStretch(1)
        lay.addWidget(widget)
        self.setCellWidget(row, col, wrap)


def context_menu(parent: QWidget, actions: list[tuple[str, str, object]]) -> QMenu:
    """Build a styled QMenu.

    ``actions`` is a list of ``(label, icon_name, callback)``; use ``("-", "", None)``
    for a separator and ``("Delete", "trash", cb)`` with a leading ``!`` on the label
    to render a destructive item.
    """
    menu = QMenu(parent)
    for text, icon_name, callback in actions:
        if text == "-":
            menu.addSeparator()
            continue
        destructive = text.startswith("!")
        clean = text[1:] if destructive else text
        color = theme.palette.danger if destructive else theme.palette.text_secondary
        act = QAction(clean, menu)
        if icon_name:
            act.setIcon(icons.icon(icon_name, color, 16))
        if callback:
            act.triggered.connect(callback)  # type: ignore[arg-type]
        menu.addAction(act)
    return menu
