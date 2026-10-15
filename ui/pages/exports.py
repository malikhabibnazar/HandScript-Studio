"""Exports — history of generated batches with filters and row actions."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QStackedWidget, QWidget

from ui.app_context import AppContext
from ui.components import (
    Button,
    DataTable,
    EmptyState,
    IconButton,
    PageHeader,
    Select,
    confirm,
    context_menu,
    label,
    status_badge,
)
from ui.pages.base import ContentPage
from ui.pages.documents import fmt_date


class ExportsPage(ContentPage):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        self._status = "All"
        self._fmt = "All"

        header = PageHeader("Exports", "Every batch you have generated and where it was saved.")
        self.add(header)
        self.add(self._build_toolbar())

        self._stack = QStackedWidget()
        self._table = DataTable(
            ["Batch", "Date", "Files", "Format", "Status", "Location", ""])
        self._table.set_stretch({
            0: QHeaderView.Stretch, 1: QHeaderView.ResizeToContents,
            2: QHeaderView.ResizeToContents, 3: QHeaderView.ResizeToContents,
            4: QHeaderView.Fixed, 5: QHeaderView.Stretch,
            6: QHeaderView.Fixed,
        })
        self._table.setColumnWidth(4, 124)
        self._table.setColumnWidth(6, 52)
        self._empty = EmptyState("No exports yet",
                                 "Generated batches will appear here with their output location.",
                                 icon_name="exports", action="Start a Batch", action_icon="batch")
        self._empty.action_button.clicked.connect(lambda: self.ctx.navigate("batch"))
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        self.add(self._stack)
        self.add_stretch(1)
        self._refresh()

    def on_show(self) -> None:
        self._refresh()

    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(label("Date", "muted"))
        date = Select(["All time", "Last 7 days", "Last 30 days", "This year"])
        date.setFixedWidth(150)
        lay.addWidget(date)
        lay.addSpacing(6)
        lay.addWidget(label("Status", "muted"))
        status = Select(["All", "Completed", "Partial", "Failed"])
        status.setFixedWidth(130)
        status.currentTextChanged.connect(lambda t: (self._set_status(t)))
        lay.addWidget(status)
        lay.addSpacing(6)
        lay.addWidget(label("Format", "muted"))
        fmt = Select(["All", "PDF", "PNG", "Combined PDF"])
        fmt.setFixedWidth(140)
        fmt.currentTextChanged.connect(lambda t: self._set_fmt(t))
        lay.addWidget(fmt)
        lay.addStretch(1)
        return w

    def _set_status(self, value: str) -> None:
        self._status = value
        self._refresh()

    def _set_fmt(self, value: str) -> None:
        self._fmt = value
        self._refresh()

    def _refresh(self) -> None:
        records = self.ctx.services.exports.list_exports()
        if self._status != "All":
            records = [r for r in records if r.status == self._status]
        if self._fmt != "All":
            records = [r for r in records if r.format.value == self._fmt]
        if not records:
            self._stack.setCurrentWidget(self._empty)
            return
        self._table.setRowCount(0)
        for rec in records:
            more = IconButton("more-v", tooltip="Actions", size=30)
            more.clicked.connect(lambda _=False, r=rec, b=more: self._menu(r, b))
            self._table.add_row([
                rec.batch_name, fmt_date(rec.date), f"{rec.file_count:,}",
                rec.format.value, status_badge(rec.status), rec.output_dir, None,
            ])
            row = self._table.rowCount() - 1
            self._table.set_actions_widget(row, 6, more)
            name_item = self._table.item(row, 0)
            font = name_item.font()
            font.setWeight(font.Weight.DemiBold)
            name_item.setFont(font)
            self._table.item(row, 0).setData(Qt.UserRole, rec.id)
        self._stack.setCurrentWidget(self._table)

    def _menu(self, rec, anchor: QWidget) -> None:
        menu = context_menu(self, [
            ("Open folder", "folder-open", lambda: self.ctx.toast("Opening folder…", "info")),
            ("View files", "documents", lambda: self.ctx.toast(f"{rec.file_count} files", "info")),
            ("Export again", "refresh", lambda: self.ctx.navigate("batch")),
            ("-", "", None),
            ("!Delete history", "trash", lambda: self._delete(rec)),
        ])
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomRight()))

    def _delete(self, rec) -> None:
        if confirm(self, "Delete export history?",
                   f"This removes the history entry for “{rec.batch_name}”. "
                   "Files on disk are not deleted.",
                   confirm_text="Delete", destructive=True):
            self.ctx.services.exports.delete_export(rec.id)
            self.ctx.toast("History entry removed", "success")
            self._refresh()
