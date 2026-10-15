"""Shared page scaffolding."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext


class ContentPage(QWidget):
    """A vertically scrolling page with comfortable margins and a max content width.

    Subclasses add widgets/layouts to ``self.body``.
    """

    def __init__(self, ctx: AppContext, *, max_width: int = 1180,
                 margins: tuple[int, int, int, int] = (32, 26, 32, 32),
                 spacing: int = 22) -> None:
        super().__init__()
        self.ctx = ctx

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        viewport = QWidget()
        row = QHBoxLayout(viewport)
        row.setContentsMargins(*margins)
        row.setSpacing(0)
        row.addStretch(1)

        column = QWidget()
        column.setMaximumWidth(max_width)
        self.body = QVBoxLayout(column)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(spacing)
        row.addWidget(column, stretch=1000)
        row.addStretch(1)

        scroll.setWidget(viewport)

    # convenience
    def add(self, widget: QWidget) -> QWidget:
        self.body.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self.body.addLayout(layout)

    def add_stretch(self, stretch: int = 1) -> None:
        self.body.addStretch(stretch)
