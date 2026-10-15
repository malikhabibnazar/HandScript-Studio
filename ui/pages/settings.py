"""Settings — categorised preferences with a native left-nav layout."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext
from ui.components import (
    Button,
    Card,
    SectionHeader,
    SegmentedControl,
    Select,
    ToggleSwitch,
    hline,
    label,
)
from ui.theme import icons, theme

CATEGORIES = [
    ("general", "General", "settings"),
    ("appearance", "Appearance", "palette"),
    ("generation", "Generation", "batch"),
    ("storage", "Storage", "database"),
    ("printing", "Printing", "printer"),
    ("about", "About", "info"),
]


class _CatButton(QPushButton):
    def __init__(self, text: str, icon_name: str) -> None:
        super().__init__(text)
        self._icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        p = theme.palette
        self.setIcon(icons.icon(icon_name, p.text_secondary, 18))
        self.setStyleSheet(
            "QPushButton { text-align: left; padding: 0 12px; border: none; border-radius: 2px;"
            f" background: transparent; color: {p.text_secondary}; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {p.control_hover}; }}"
            f"QPushButton:checked {{ background: {p.accent_soft}; color: {p.accent_text}; }}")


class SettingsPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # left category nav
        nav = QFrame()
        nav.setFixedWidth(220)
        nav.setStyleSheet(f"background: {theme.palette.surface}; "
                          f"border-right: 1px solid {theme.palette.border};")
        nl = QVBoxLayout(nav)
        nl.setContentsMargins(14, 22, 14, 14)
        nl.setSpacing(4)
        title = label("Settings", "subtitle")
        title.setContentsMargins(8, 0, 0, 0)
        nl.addWidget(title)
        nl.addSpacing(12)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, (key, text, icon_name) in enumerate(CATEGORIES):
            btn = _CatButton(text, icon_name)
            if i == 0:
                btn.setChecked(True)
            self._group.addButton(btn, i)
            nl.addWidget(btn)
        nl.addStretch(1)
        self._group.idClicked.connect(self._switch)
        root.addWidget(nav)

        # right content
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_general())
        self._stack.addWidget(self._page_appearance())
        self._stack.addWidget(self._page_generation())
        self._stack.addWidget(self._page_storage())
        self._stack.addWidget(self._page_printing())
        self._stack.addWidget(self._page_about())
        root.addWidget(self._stack, stretch=1)

    def _switch(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    # ------------------------------------------------------------- scaffolding
    def _scroll(self, build) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(32, 28, 32, 32)
        row.addStretch(1)
        col = QWidget()
        col.setMaximumWidth(680)
        self._col_layout = QVBoxLayout(col)
        self._col_layout.setContentsMargins(0, 0, 0, 0)
        self._col_layout.setSpacing(18)
        build(self._col_layout)
        self._col_layout.addStretch(1)
        row.addWidget(col, stretch=1000)
        row.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _setting_row(self, title: str, subtitle: str, control: QWidget) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(16)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = label(title, "body")
        t.setStyleSheet("font-weight: 600;")
        t.setWordWrap(False)
        col.addWidget(t)
        if subtitle:
            col.addWidget(label(subtitle, "muted"))
        lay.addLayout(col, stretch=1)
        lay.addWidget(control, alignment=Qt.AlignRight | Qt.AlignVCenter)
        return w

    def _field_input(self, value: str, trailing_icon: str | None = None) -> QLineEdit:
        edit = QLineEdit(value)
        edit.setFixedWidth(300)
        if trailing_icon:
            edit.addAction(icons.icon(trailing_icon, theme.palette.text_muted, 16),
                           QLineEdit.TrailingPosition)
        return edit

    # ------------------------------------------------------------------ pages
    def _page_general(self) -> QWidget:
        def build(col):
            card = Card(padding=22, spacing=6)
            card.add(SectionHeader("Workspace & defaults"))
            card.add(hline())
            card.add(self._setting_row("Application workspace", "Where profiles and data live",
                                       self._field_input("~/Documents/HandScript", "folder")))
            card.add(hline())
            card.add(self._setting_row("Default output directory", "New batches save here by default",
                                       self._field_input("~/Documents/HandScript/Exports", "folder")))
            card.add(hline())
            card.add(self._setting_row("Default template", "",
                                       self._select(["Thank-You Card", "Event Invitation",
                                                     "Standard #10 Envelope"], 180)))
            card.add(hline())
            card.add(self._setting_row("Default handwriting profile", "",
                                       self._select(["Amelia — Casual Script",
                                                     "Theodore — Formal Print"], 220)))
            col.addWidget(card)
        return self._scroll(build)

    def _page_appearance(self) -> QWidget:
        def build(col):
            card = Card(padding=22, spacing=6)
            card.add(SectionHeader("Appearance"))
            card.add(hline())
            theme_seg = SegmentedControl(["Light", "Dark", "System"])
            theme_seg.set_current(1 if self.ctx.current_theme() == "dark" else 0)
            theme_seg.changed.connect(self._on_theme)
            card.add(self._setting_row("Theme", "Switch between light and dark appearance",
                                       theme_seg))
            card.add(hline())
            scale = QSlider(Qt.Horizontal)
            scale.setRange(80, 140)
            scale.setValue(100)
            scale.setFixedWidth(220)
            card.add(self._setting_row("UI scale", "Adjust interface size", scale))
            card.add(hline())
            card.add(self._setting_row("Reduce motion", "Minimise animations and transitions",
                                       ToggleSwitch(False)))
            col.addWidget(card)
        return self._scroll(build)

    def _page_generation(self) -> QWidget:
        def build(col):
            card = Card(padding=22, spacing=6)
            card.add(SectionHeader("Generation defaults"))
            card.add(hline())
            card.add(self._setting_row("Default export format", "",
                                       self._select(["PDF", "PNG", "Combined PDF"], 160)))
            card.add(hline())
            card.add(self._setting_row("Default resolution", "",
                                       self._select(["150 dpi", "300 dpi", "600 dpi"], 160, 1)))
            card.add(hline())
            card.add(self._setting_row("Pause on first error", "Stop the batch if an item fails",
                                       ToggleSwitch(False)))
            card.add(hline())
            card.add(self._setting_row("Open folder when complete",
                                       "Reveal output in Finder after generation",
                                       ToggleSwitch(True)))
            col.addWidget(card)
        return self._scroll(build)

    def _page_storage(self) -> QWidget:
        def build(col):
            card = Card(padding=22, spacing=6)
            card.add(SectionHeader("Local data"))
            card.add(hline())
            card.add(self._setting_row("Local data location", "SQLite database & assets",
                                       self._field_input("~/Library/HandScript", "folder")))
            card.add(hline())
            card.add(self._setting_row("Cache size", "Rendered previews and thumbnails",
                                       label("248 MB", "secondary")))
            card.add(hline())
            clear = Button("Clear cache", variant="dangerGhost", icon_name="trash", size="sm")
            clear.clicked.connect(lambda: self.ctx.toast("Cache cleared (248 MB freed)", "success"))
            card.add(self._setting_row("Clear cache", "Safe to clear at any time", clear))
            col.addWidget(card)
        return self._scroll(build)

    def _page_printing(self) -> QWidget:
        def build(col):
            card = Card(padding=22, spacing=6)
            card.add(SectionHeader("Printing"))
            card.add(hline())
            card.add(self._setting_row("Default printer", "",
                                       self._select(["System Default", "Office LaserJet",
                                                     "Photo Printer"], 200)))
            card.add(hline())
            card.add(self._setting_row("Page scaling", "",
                                       self._select(["Actual size", "Fit to page",
                                                     "Shrink oversized"], 180)))
            card.add(hline())
            card.add(self._setting_row("Print margins", "",
                                       self._select(["None", "Minimal", "Standard"], 160, 1)))
            col.addWidget(card)
        return self._scroll(build)

    def _page_about(self) -> QWidget:
        def build(col):
            p = theme.palette
            card = Card(padding=24, spacing=14)
            head = QHBoxLayout()
            head.setSpacing(14)
            logo = label("")
            logo.setFixedSize(52, 52)
            logo.setPixmap(icons.pixmap("handwriting", "#FFFFFF", 28))
            logo.setAlignment(Qt.AlignCenter)
            logo.setStyleSheet(f"background: {p.accent}; border-radius: 2px;")
            head.addWidget(logo)
            col2 = QVBoxLayout()
            col2.setSpacing(2)
            name = label("HandScript Studio", "subtitle")
            name.setWordWrap(False)
            col2.addWidget(name)
            col2.addWidget(label("Version 0.9.0 (mock preview build)", "muted"))
            head.addLayout(col2)
            head.addStretch(1)
            card.add_layout(head)
            card.add(hline())
            card.add(self._info_row("System", "macOS 14 · Apple Silicon"))
            card.add(self._info_row("Rendering engine", "Mock engine v0.9 (local)"))
            card.add(self._info_row("Python runtime", "3.12 · PySide6 / Qt 6"))
            card.add(hline())
            links = QHBoxLayout()
            links.setSpacing(10)
            docs = Button("Documentation", variant="secondary", icon_name="documents")
            docs.clicked.connect(lambda: self.ctx.toast("Opening documentation…", "info"))
            support = Button("Contact Support", variant="ghost", icon_name="help")
            support.clicked.connect(lambda: self.ctx.toast("Opening support…", "info"))
            links.addWidget(docs)
            links.addWidget(support)
            links.addStretch(1)
            card.add_layout(links)
            col.addWidget(card)
        return self._scroll(build)

    def _info_row(self, name: str, value: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.addWidget(label(name, "secondary"))
        lay.addStretch(1)
        v = label(value, "body")
        v.setStyleSheet("font-weight: 600;")
        v.setWordWrap(False)
        lay.addWidget(v)
        return w

    def _select(self, items: list[str], width: int, index: int = 0) -> Select:
        s = Select(items)
        s.setFixedWidth(width)
        s.setCurrentIndex(index)
        return s

    def _on_theme(self, index: int) -> None:
        if index == 1:
            self.ctx.set_theme("dark")
        else:
            self.ctx.set_theme("light")
