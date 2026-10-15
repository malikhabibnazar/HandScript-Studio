"""First-launch onboarding flow."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext
from ui.components import Button, Card, Field, Select, SearchField, label
from ui.theme import card_shadow, icons, theme

_STEPS = [
    ("sparkle", "Welcome to HandScript Studio",
     "Generate beautiful, printable documents from your own handwriting styles. "
     "Let's set up your workspace — it only takes a minute."),
    ("folder", "Choose your workspace",
     "Pick a local folder where HandScript will store profiles, templates and exports. "
     "Everything stays on your Mac."),
    ("handwriting", "Add a handwriting profile",
     "Import a few samples of handwriting. The local engine analyses them to build a "
     "reusable style — no samples are sent anywhere."),
    ("templates", "Create your first template",
     "Start from a 4×6 card or a #10 envelope. You can fully customise layouts later."),
    ("check-circle", "You're all set",
     "Your workspace is ready. Jump into the dashboard to create your first document or "
     "start a batch."),
]


class OnboardingPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._index = 0

        p = theme.palette
        self.setObjectName("OnboardingPage")
        self.setStyleSheet(f"QWidget#OnboardingPage {{ background: {p.window}; }}")
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        column = QVBoxLayout()
        column.setAlignment(Qt.AlignCenter)
        root.addLayout(column)
        root.addStretch(1)

        self._card = QFrame()
        self._card.setObjectName("Card")
        self._card.setFixedSize(540, 440)
        self._card.setGraphicsEffect(card_shadow(blur=50, y=18, alpha=40))
        column.addWidget(self._card, alignment=Qt.AlignCenter)

        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(40, 36, 40, 28)
        cl.setSpacing(0)

        # dots
        self._dots_row = QHBoxLayout()
        self._dots_row.setSpacing(7)
        self._dots_row.addStretch(1)
        self._dots: list[QFrame] = []
        for _ in _STEPS:
            dot = QFrame()
            dot.setFixedSize(7, 7)
            self._dots.append(dot)
            self._dots_row.addWidget(dot)
        self._dots_row.addStretch(1)
        cl.addLayout(self._dots_row)
        cl.addSpacing(24)

        self._stack = QStackedWidget()
        for icon_name, title, desc in _STEPS:
            self._stack.addWidget(self._build_step(icon_name, title, desc))
        cl.addWidget(self._stack, stretch=1)

        # footer
        footer = QHBoxLayout()
        self._skip = Button("Skip setup", variant="ghost")
        self._skip.clicked.connect(self._finish)
        footer.addWidget(self._skip)
        footer.addStretch(1)
        self._back = Button("Back", variant="secondary")
        self._back.clicked.connect(self._go_back)
        footer.addWidget(self._back)
        self._next = Button("Continue", variant="primary", icon_name="arrow-right")
        self._next.clicked.connect(self._go_next)
        footer.addWidget(self._next)
        cl.addLayout(footer)

        self._refresh()

    def _build_step(self, icon_name: str, title: str, desc: str) -> QWidget:
        p = theme.palette
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        badge = QFrame()
        badge.setFixedSize(58, 58)
        badge.setStyleSheet(f"background: {p.accent_soft}; border-radius: 2px;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, p.accent, 28))
        ic.setAlignment(Qt.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge, alignment=Qt.AlignHCenter)

        t = label(title, "title")
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        lay.addWidget(t)

        d = label(desc, "secondary")
        d.setAlignment(Qt.AlignCenter)
        d.setWordWrap(True)
        d.setMaximumWidth(400)
        lay.addWidget(d, alignment=Qt.AlignHCenter)

        extra = self._step_extra(icon_name)
        if extra is not None:
            lay.addSpacing(4)
            lay.addWidget(extra, alignment=Qt.AlignHCenter)
        return w

    def _step_extra(self, icon_name: str) -> QWidget | None:
        if icon_name == "folder":
            field = SearchField("~/Documents/HandScript", width=360)
            field.setText("~/Documents/HandScript")
            field.addAction(icons.icon("folder", theme.palette.text_muted, 16),
                            SearchField.TrailingPosition)
            return field
        if icon_name == "templates":
            sel = Select(["4×6 Card — Thank-You", "4×6 Card — Invitation", "#10 Envelope"])
            sel.setFixedWidth(360)
            return sel
        return None

    def _refresh(self) -> None:
        self._stack.setCurrentIndex(self._index)
        p = theme.palette
        for i, dot in enumerate(self._dots):
            on = i == self._index
            dot.setStyleSheet(
                f"background: {p.accent if on else p.border_strong}; border-radius: 2px;")
            dot.setFixedWidth(18 if on else 7)
        self._back.setVisible(self._index > 0)
        last = self._index == len(_STEPS) - 1
        self._next.setText("Get started" if last else "Continue")
        self._skip.setVisible(not last)

    def _go_next(self) -> None:
        if self._index >= len(_STEPS) - 1:
            self._finish()
            return
        self._index += 1
        self._refresh()

    def _go_back(self) -> None:
        self._index = max(0, self._index - 1)
        self._refresh()

    def _finish(self) -> None:
        self.ctx.navigate("dashboard")
        self.ctx.toast("Welcome to HandScript Studio", "success")
