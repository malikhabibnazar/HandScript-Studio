"""Handwriting Profiles — grid of profile cards with handwriting previews."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from models.domain import HandwritingProfile
from ui.app_context import AppContext
from ui.components import (
    Avatar,
    Button,
    FlowLayout,
    IconButton,
    PageHeader,
    confirm,
    context_menu,
    label,
    status_badge,
)
from ui.pages.base import ContentPage
from ui.theme import icons, theme


class _HandPreview(QWidget):
    """Renders a short phrase in the handwriting font on a subtle ruled card."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setFixedHeight(96)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.fillRect(self.rect(), QColor(p.surface_alt))
        # baseline
        painter.setPen(QColor(p.border))
        y = int(self.height() * 0.68)
        painter.drawLine(16, y, self.width() - 16, y)
        f = QFont(theme.type.handwriting)
        f.setPixelSize(26)
        painter.setFont(f)
        painter.setPen(QColor(p.text))
        painter.drawText(self.rect().adjusted(18, 0, -18, int(self.height() * 0.1)),
                         Qt.AlignVCenter | Qt.AlignLeft, self._text)
        painter.end()


class ProfileCard(QFrame):
    open_requested = Signal(str)
    menu_requested = Signal(object, QWidget)

    def __init__(self, profile: HandwritingProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile = profile
        self.setObjectName("Card")
        self.setFixedWidth(300)
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        preview = _HandPreview(profile.preview_text)
        preview.setStyleSheet("border-top-left-radius: 2px; border-top-right-radius: 2px;")
        lay.addWidget(preview)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 14, 12, 14)
        bl.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(Avatar(profile.name, 38))
        col = QVBoxLayout()
        col.setSpacing(1)
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name = label(profile.name, "body")
        name.setStyleSheet("font-weight: 600;")
        name.setWordWrap(False)
        name_row.addWidget(name)
        if profile.is_default:
            star = label("")
            star.setPixmap(icons.pixmap("star-fill", theme.palette.warning, 14))
            star.setToolTip("Default profile")
            name_row.addWidget(star)
        name_row.addStretch(1)
        col.addLayout(name_row)
        col.addWidget(label(f"{profile.sample_count} samples", "muted"))
        top.addLayout(col, stretch=1)
        bl.addLayout(top)

        meta = QHBoxLayout()
        meta.addWidget(status_badge(profile.status.value))
        meta.addStretch(1)
        more = IconButton("more-v", tooltip="Actions", size=30)
        more.clicked.connect(lambda: self.menu_requested.emit(profile, more))
        meta.addWidget(more)
        bl.addLayout(meta)
        lay.addWidget(body)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.open_requested.emit(self._profile.id)


class HandwritingProfilesPage(ContentPage):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        header = PageHeader(
            "Handwriting Profiles",
            "Styles built from your handwriting samples by the local processing engine.")
        add = Button("Add Handwriting Profile", variant="primary", icon_name="plus")
        add.clicked.connect(lambda: self.ctx.toast("New profile — add samples to begin", "info"))
        header.add_action(add)
        self.add(header)

        self._host = QWidget()
        self._flow = FlowLayout(self._host, h_spacing=16, v_spacing=16)
        self.add(self._host)
        self.add_stretch(1)
        self._refresh()

    def on_show(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        while self._flow.count():
            item = self._flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for profile in self.ctx.services.handwriting.list_profiles():
            card = ProfileCard(profile)
            card.open_requested.connect(
                lambda pid: self.ctx.navigate("handwriting_detail", profile_id=pid))
            card.menu_requested.connect(self._menu)
            self._flow.addWidget(card)

    def _menu(self, profile, anchor: QWidget) -> None:
        menu = context_menu(self, [
            ("Open", "open", lambda: self.ctx.navigate("handwriting_detail", profile_id=profile.id)),
            ("Preview", "eye", lambda: self.ctx.navigate("handwriting_detail", profile_id=profile.id)),
            ("Set as default", "star", lambda: self._set_default(profile)),
            ("Rename", "text", lambda: self.ctx.toast("Rename — coming soon", "info")),
            ("Duplicate", "duplicate", lambda: self.ctx.toast("Profile duplicated", "success")),
            ("-", "", None),
            ("!Delete", "trash", lambda: self._delete(profile)),
        ])
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomRight()))

    def _set_default(self, profile) -> None:
        self.ctx.services.handwriting.set_default(profile.id)
        self.ctx.toast(f"“{profile.name}” is now the default", "success")
        self._refresh()

    def _delete(self, profile) -> None:
        if confirm(self, "Delete profile?",
                   f"“{profile.name}” and its samples will be removed.",
                   confirm_text="Delete", destructive=True):
            self.ctx.services.handwriting.delete_profile(profile.id)
            self.ctx.toast("Profile deleted", "success")
            self._refresh()
