"""Reusable dialogs: a styled modal base and a confirmation dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ui.theme import card_shadow, icons, theme

from .buttons import Button, IconButton
from .common import label


class Modal(QDialog):
    """A frameless, card-styled modal with a title bar and body/footer slots."""

    def __init__(self, title: str, *, subtitle: str = "", width: int = 440,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(width)
        card.setGraphicsEffect(card_shadow(blur=48, y=16, alpha=60))
        outer.addWidget(card)

        self._v = QVBoxLayout(card)
        self._v.setContentsMargins(24, 22, 24, 22)
        self._v.setSpacing(16)

        head = QHBoxLayout()
        head.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(label(title, "subtitle"))
        if subtitle:
            sub = label(subtitle, "secondary")
            col.addWidget(sub)
        head.addLayout(col)
        head.addStretch(1)
        close = IconButton("close", size=28, icon_size=15, color=theme.palette.text_muted)
        close.clicked.connect(self.reject)
        head.addWidget(close, alignment=Qt.AlignTop)
        self._v.addLayout(head)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        self._v.addLayout(self.body)

        self.footer = QHBoxLayout()
        self.footer.setSpacing(10)
        self.footer.addStretch(1)
        self._v.addLayout(self.footer)

    def add_body(self, widget: QWidget) -> QWidget:
        self.body.addWidget(widget)
        return widget

    def add_footer_button(self, button: Button) -> Button:
        self.footer.addWidget(button)
        return button


class ConfirmDialog(Modal):
    def __init__(self, title: str, message: str, *, confirm_text: str = "Confirm",
                 destructive: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(title, parent=parent, width=420)
        self.add_body(label(message, "secondary"))
        cancel = Button("Cancel", variant="secondary")
        cancel.clicked.connect(self.reject)
        confirm = Button(confirm_text, variant="danger" if destructive else "primary")
        confirm.clicked.connect(self.accept)
        self.add_footer_button(cancel)
        self.add_footer_button(confirm)


def confirm(parent: QWidget, title: str, message: str, *, confirm_text: str = "Confirm",
            destructive: bool = False) -> bool:
    dlg = ConfirmDialog(title, message, confirm_text=confirm_text,
                        destructive=destructive, parent=parent)
    return dlg.exec() == QDialog.Accepted
