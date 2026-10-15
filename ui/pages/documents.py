"""Documents — management list with search, filters, sorting and bulk actions."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext
from ui.components import (
    Button,
    DataTable,
    EmptyState,
    FilterChip,
    IconButton,
    LoadingState,
    PageHeader,
    SearchField,
    Select,
    confirm,
    context_menu,
    label,
    status_badge,
)
from ui.pages.base import ContentPage
from ui.theme import theme

STATUS_FILTERS = ["Draft", "Ready", "Generating", "Completed", "Failed"]


def fmt_date(dt: datetime) -> str:
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


class DocumentsPage(ContentPage):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        self._search = ""
        self._active_statuses: set[str] = set()
        self._sort = 0

        header = PageHeader("Documents", "Create, organise and export your documents.")
        imp = Button("Import", variant="secondary", icon_name="download")
        imp.clicked.connect(lambda: self.ctx.navigate("batch"))
        create = Button("Create Document", variant="primary", icon_name="plus")
        create.clicked.connect(lambda: self.ctx.navigate("document_editor", document_id=None))
        header.add_action(imp)
        header.add_action(create)
        self.add(header)

        self.add(self._build_toolbar())
        self._bulk_bar = self._build_bulk_bar()
        self.add(self._bulk_bar)

        self._stack = QStackedWidget()
        self._loading = LoadingState("Loading documents…")
        self._table = self._build_table()
        self._empty = EmptyState(
            "No documents yet",
            "Create your first document from a template, or import a data list to generate in bulk.",
            icon_name="documents", action="Create Document", action_icon="plus")
        self._empty.action_button.clicked.connect(
            lambda: self.ctx.navigate("document_editor", document_id=None))
        self._no_results = EmptyState(
            "No matching documents",
            "Try adjusting your search or filters.",
            icon_name="search")
        for w in (self._loading, self._table, self._empty, self._no_results):
            self._stack.addWidget(w)
        self.add(self._stack)
        self.add_stretch(1)

        self._stack.setCurrentWidget(self._loading)
        QTimer.singleShot(420, self._refresh)

    # ------------------------------------------------------------------ build
    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(10)
        self._search_field = SearchField("Search documents…", width=300)
        self._search_field.textChanged.connect(self._on_search)
        row.addWidget(self._search_field)
        row.addStretch(1)
        sort = Select(["Recently modified", "Name A–Z", "Status"])
        sort.setFixedWidth(180)
        sort.currentIndexChanged.connect(self._on_sort)
        row.addWidget(label("Sort", "muted"))
        row.addWidget(sort)
        lay.addLayout(row)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        for status in STATUS_FILTERS:
            chip = FilterChip(status)
            chip.toggled.connect(lambda on, s=status: self._on_filter(s, on))
            chips.addWidget(chip)
        chips.addStretch(1)
        lay.addLayout(chips)
        return w

    def _build_bulk_bar(self) -> QFrame:
        p = theme.palette
        bar = QFrame()
        bar.setObjectName("BulkBar")
        bar.setStyleSheet(
            f"QFrame#BulkBar {{ background: {p.accent_soft}; border: 1px solid {p.accent};"
            f" border-radius: 2px; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 8, 10, 8)
        lay.setSpacing(10)
        self._bulk_label = label("0 selected", "body")
        self._bulk_label.setStyleSheet(f"color: {p.accent_text}; font-weight: 600;")
        lay.addWidget(self._bulk_label)
        lay.addStretch(1)
        export_btn = Button("Export", variant="soft", icon_name="share", size="sm")
        export_btn.clicked.connect(self._bulk_export)
        delete_btn = Button("Delete", variant="dangerGhost", icon_name="trash", size="sm")
        delete_btn.clicked.connect(self._bulk_delete)
        clear_btn = IconButton("close", tooltip="Clear selection", size=28, icon_size=14)
        clear_btn.clicked.connect(lambda: self._table.clearSelection())
        lay.addWidget(export_btn)
        lay.addWidget(delete_btn)
        lay.addWidget(clear_btn)
        bar.setVisible(False)
        return bar

    def _build_table(self) -> DataTable:
        table = DataTable(
            ["Document", "Template", "Profile", "Created", "Status", "Format", ""])
        table.set_stretch({
            0: QHeaderView.Stretch,
            1: QHeaderView.ResizeToContents,
            2: QHeaderView.ResizeToContents,
            3: QHeaderView.ResizeToContents,
            4: QHeaderView.Fixed,
            5: QHeaderView.ResizeToContents,
            6: QHeaderView.Fixed,
        })
        table.setColumnWidth(4, 132)
        table.setColumnWidth(6, 52)
        table.itemSelectionChanged.connect(self._on_selection)
        table.cellDoubleClicked.connect(self._on_double_click)
        return table

    # --------------------------------------------------------------- data flow
    def on_show(self) -> None:
        self._refresh()

    def _visible_docs(self) -> list:
        docs = self.ctx.services.documents.list_documents()
        if self._search:
            q = self._search.lower()
            docs = [d for d in docs if q in d.name.lower() or q in d.template.lower()
                    or q in d.profile.lower()]
        if self._active_statuses:
            docs = [d for d in docs if d.status.value in self._active_statuses]
        if self._sort == 1:
            docs.sort(key=lambda d: d.name.lower())
        elif self._sort == 2:
            docs.sort(key=lambda d: d.status.value)
        else:
            docs.sort(key=lambda d: d.modified, reverse=True)
        return docs

    def _refresh(self) -> None:
        all_docs = self.ctx.services.documents.list_documents()
        if not all_docs:
            self._stack.setCurrentWidget(self._empty)
            return
        docs = self._visible_docs()
        if not docs:
            self._stack.setCurrentWidget(self._no_results)
            return
        self._populate(docs)
        self._stack.setCurrentWidget(self._table)

    def _populate(self, docs: list) -> None:
        self._table.setRowCount(0)
        for doc in docs:
            more = IconButton("more-v", tooltip="Actions", size=30, icon_size=18)
            more.clicked.connect(lambda _=False, d=doc, b=more: self._row_menu(d, b))
            self._table.add_row([
                doc.name, doc.template, doc.profile, fmt_date(doc.created),
                status_badge(doc.status.value), doc.export_format.value, None,
            ])
            row = self._table.rowCount() - 1
            self._table.set_actions_widget(row, 6, more)
            self._table.item(row, 0).setData(Qt.UserRole, doc.id)
            # emphasise the name
            name_item = self._table.item(row, 0)
            font = name_item.font()
            font.setWeight(font.Weight.DemiBold)
            name_item.setFont(font)

    # ---------------------------------------------------------------- handlers
    def _on_search(self, text: str) -> None:
        self._search = text.strip()
        self._refresh()

    def _on_sort(self, index: int) -> None:
        self._sort = index
        self._refresh()

    def _on_filter(self, status: str, on: bool) -> None:
        if on:
            self._active_statuses.add(status)
        else:
            self._active_statuses.discard(status)
        self._refresh()

    def _on_selection(self) -> None:
        rows = {i.row() for i in self._table.selectedItems()}
        n = len(rows)
        self._bulk_bar.setVisible(n > 0)
        self._bulk_label.setText(f"{n} selected")

    def _on_double_click(self, row: int, _col: int) -> None:
        item = self._table.item(row, 0)
        if item:
            self.ctx.navigate("document_editor", document_id=item.data(Qt.UserRole))

    def _row_menu(self, doc, anchor: QWidget) -> None:
        menu = context_menu(self, [
            ("Open", "open", lambda: self.ctx.navigate("document_editor", document_id=doc.id)),
            ("Duplicate", "duplicate", lambda: self._duplicate(doc)),
            ("Export", "share", lambda: self.ctx.toast(f"Exporting “{doc.name}”…", "info")),
            ("-", "", None),
            ("!Delete", "trash", lambda: self._delete(doc)),
        ])
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomRight()))

    def _duplicate(self, doc) -> None:
        self.ctx.services.documents.duplicate_document(doc.id)
        self.ctx.toast(f"Duplicated “{doc.name}”", "success")
        self._refresh()

    def _delete(self, doc) -> None:
        if confirm(self, "Delete document?",
                   f"“{doc.name}” will be permanently removed. This cannot be undone.",
                   confirm_text="Delete", destructive=True):
            self.ctx.services.documents.delete_document(doc.id)
            self.ctx.toast("Document deleted", "success")
            self._refresh()

    def _selected_ids(self) -> list[str]:
        rows = {i.row() for i in self._table.selectedItems()}
        ids = []
        for r in rows:
            item = self._table.item(r, 0)
            if item:
                ids.append(item.data(Qt.UserRole))
        return ids

    def _bulk_export(self) -> None:
        n = len(self._selected_ids())
        self.ctx.toast(f"Exporting {n} document(s)…", "info")

    def _bulk_delete(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        if confirm(self, "Delete documents?",
                   f"{len(ids)} document(s) will be permanently removed.",
                   confirm_text="Delete", destructive=True):
            for doc_id in ids:
                self.ctx.services.documents.delete_document(doc_id)
            self.ctx.toast(f"Deleted {len(ids)} document(s)", "success")
            self._refresh()
