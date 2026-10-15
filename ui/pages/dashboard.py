"""Dashboard — overview, recent activity, quick actions and system status."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from ui.app_context import AppContext
from ui.components import (
    Button,
    Card,
    LoadingState,
    PageHeader,
    QuickActionTile,
    SectionHeader,
    StatCard,
    StatusRow,
    hline,
    label,
)
from ui.pages.base import ContentPage
from ui.theme import icons, theme

_ACT_ICON = {
    "batch": ("batch", "accent"), "document": ("documents", "info"),
    "template": ("templates", "neutral"), "import": ("download", "success"),
    "error": ("warning", "danger"),
}


def _relative(when: datetime) -> str:
    delta = datetime.now() - when
    secs = delta.total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


class DashboardPage(ContentPage):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        self._loading = LoadingState("Loading your workspace…")
        self.add(self._loading)
        self.add_stretch(1)
        QTimer.singleShot(480, self._build_content)

    def _build_content(self) -> None:
        self._loading.stop()
        self._loading.setParent(None)
        # clear stretch
        while self.body.count():
            item = self.body.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        header = PageHeader(
            "Dashboard",
            "Generate printable documents from editable templates and your handwriting styles.",
        )
        start = Button("Start Batch", variant="secondary", icon_name="batch")
        start.clicked.connect(lambda: self.ctx.navigate("batch"))
        create = Button("Create Document", variant="primary", icon_name="plus")
        create.clicked.connect(lambda: self.ctx.navigate("document_editor", document_id=None))
        header.add_action(start)
        header.add_action(create)
        self.add(header)

        self._add_overview()
        self._add_main_columns()
        self.add_stretch(1)

    def _add_overview(self) -> None:
        counts = self.ctx.services.dashboard.counts()
        grid = QGridLayout()
        grid.setSpacing(16)
        cards = [
            ("Handwriting Profiles", str(counts["profiles"]), "handwriting", "accent", ""),
            ("Templates", str(counts["templates"]), "templates", "neutral", ""),
            ("Documents Generated", f'{counts["documents_generated"]:,}', "documents",
             "success", "+128 this week"),
            ("Recent Batches", str(counts["recent_batches"]), "batch", "warning", ""),
        ]
        for i, (title, value, icon_name, tone, delta) in enumerate(cards):
            grid.addWidget(StatCard(title, value, icon_name, tone=tone, delta=delta), 0, i)
            grid.setColumnStretch(i, 1)
        self.add_layout(grid)

    def _add_main_columns(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._activity_card(), stretch=3)
        right = QVBoxLayout()
        right.setSpacing(16)
        right.addWidget(self._quick_actions_card())
        right.addWidget(self._status_card())
        right.addStretch(1)
        row.addLayout(right, stretch=2)
        self.add_layout(row)

    def _activity_card(self) -> Card:
        card = Card(padding=20, spacing=4)
        card.add(SectionHeader("Recent activity", subtitle="Across documents, templates and imports"))
        card.add(hline())
        activity = self.ctx.services.dashboard.activity()
        for i, item in enumerate(activity):
            card.add(self._activity_row(item))
            if i < len(activity) - 1:
                card.add(hline())
        return card

    def _activity_row(self, item) -> QWidget:
        p = theme.palette
        icon_name, tone = _ACT_ICON.get(item.kind, ("dot", "neutral"))
        fg = {"accent": p.accent, "info": p.info, "success": p.success,
              "danger": p.danger, "neutral": p.text_secondary}[tone]
        soft = {"accent": p.accent_soft, "info": p.info_soft, "success": p.success_soft,
                "danger": p.danger_soft, "neutral": p.neutral_soft}[tone]
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(12)
        badge = QWidget()
        badge.setFixedSize(34, 34)
        badge.setStyleSheet(f"background: {soft}; border-radius: 2px;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, fg, 17))
        ic.setAlignment(Qt.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge)

        col = QVBoxLayout()
        col.setSpacing(1)
        t = label(item.title, "body")
        t.setStyleSheet("font-weight: 600;")
        t.setWordWrap(False)
        col.addWidget(t)
        col.addWidget(label(item.detail, "muted"))
        lay.addLayout(col, stretch=1)

        when = label(_relative(item.when), "caption")
        when.setWordWrap(False)
        lay.addWidget(when, alignment=Qt.AlignTop)
        return w

    def _quick_actions_card(self) -> Card:
        card = Card(padding=20, spacing=10)
        card.add(SectionHeader("Quick actions"))
        tiles = [
            ("New Document", "Start from a template", "documents",
             lambda: self.ctx.navigate("document_editor", document_id=None)),
            ("New Template", "Design a layout", "templates",
             lambda: self.ctx.navigate("template_editor", template_id=None)),
            ("Import Data", "Load a TXT or CSV list", "download",
             lambda: self.ctx.navigate("batch")),
            ("Manage Handwriting", "Profiles & samples", "handwriting",
             lambda: self.ctx.navigate("handwriting")),
            ("Start Batch Generation", "Generate in bulk", "batch",
             lambda: self.ctx.navigate("batch")),
        ]
        for title, subtitle, icon_name, cb in tiles:
            tile = QuickActionTile(title, subtitle, icon_name)
            tile.clicked.connect(cb)
            card.add(tile)
        return card

    def _status_card(self) -> Card:
        card = Card(padding=20, spacing=12)
        card.add(SectionHeader("System status"))
        card.add(StatusRow("Rendering Engine", "Ready", "success", detail="mock v0.9"))
        card.add(StatusRow("Local Storage", "Healthy", "success", detail="2.4 GB free"))
        card.add(StatusRow("Export System", "Idle", "neutral"))
        return card
