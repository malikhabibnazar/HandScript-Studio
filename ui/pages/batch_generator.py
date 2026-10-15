"""Batch Generator — a five-step generation wizard."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext
from ui.components import (
    Badge,
    Button,
    Card,
    DataTable,
    Field,
    PageHeader,
    Select,
    SectionHeader,
    Stepper,
    ToggleSwitch,
    hline,
    label,
)
from ui.components.canvas import DocumentCanvas
from ui.pages.base import ContentPage
from ui.theme import icons, theme

STEPS = ["Template", "Handwriting", "Import Data", "Output", "Review"]


class OptionRow(QFrame):
    """A single-select option with icon, title, subtitle and radio indicator."""

    selected = Signal(str)

    def __init__(self, key: str, title: str, subtitle: str, icon_name: str, *,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._key = key
        self._active = False
        self.setObjectName("Option")
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)
        p = theme.palette
        self._badge = QFrame()
        self._badge.setFixedSize(38, 38)
        self._badge.setStyleSheet(f"background: {p.surface_alt}; border-radius: 2px;")
        bl = QVBoxLayout(self._badge)
        bl.setContentsMargins(0, 0, 0, 0)
        self._icon = label("")
        self._icon.setPixmap(icons.pixmap(icon_name, p.text_secondary, 19))
        self._icon.setAlignment(Qt.AlignCenter)
        bl.addWidget(self._icon)
        lay.addWidget(self._badge)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = label(title, "body")
        t.setStyleSheet("font-weight: 600;")
        t.setWordWrap(False)
        col.addWidget(t)
        col.addWidget(label(subtitle, "muted"))
        lay.addLayout(col, stretch=1)
        self._radio = QFrame()
        self._radio.setFixedSize(20, 20)
        lay.addWidget(self._radio)
        self._icon_name = icon_name
        self._restyle()

    def _restyle(self) -> None:
        p = theme.palette
        if self._active:
            self.setStyleSheet(
                f"QFrame#Option {{ background: {p.accent_soft}; border: 1px solid {p.accent};"
                " border-radius: 2px; }")
            self._radio.setStyleSheet(
                f"background: {p.accent}; border-radius: 2px; border: 5px solid {p.accent_soft};")
            self._icon.setPixmap(icons.pixmap(self._icon_name, p.accent, 19))
        else:
            self.setStyleSheet(
                f"QFrame#Option {{ background: {p.surface}; border: 1px solid {p.border};"
                " border-radius: 2px; }"
                f"QFrame#Option:hover {{ border-color: {p.border_strong}; }}")
            self._radio.setStyleSheet(
                f"background: transparent; border: 2px solid {p.border_strong}; border-radius: 2px;")
            self._icon.setPixmap(icons.pixmap(self._icon_name, p.text_secondary, 19))

    def set_active(self, active: bool) -> None:
        self._active = active
        self._restyle()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.selected.emit(self._key)


class BatchGeneratorPage(ContentPage):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        self._step = 0
        self._state: dict = {
            "template": None, "profile": None, "import": None,
            "format": "PDF", "output_dir": "~/HandScript/Exports/new-batch",
            "naming": "document_{index}", "individual": True, "combined": False,
            "envelope": False, "quality": "Standard · 300 dpi",
        }

        self.add(PageHeader(
            "Batch Generator",
            "Generate documents for an entire data list in five steps."))
        self._stepper = Stepper(STEPS)
        self.add(self._stepper)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._step_template())
        self._stack.addWidget(self._step_profile())
        self._stack.addWidget(self._step_import())
        self._stack.addWidget(self._step_output())
        self._review_host = QWidget()
        self._review_layout = QVBoxLayout(self._review_host)
        self._review_layout.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._review_host)
        self.add(self._stack)

        self.add(self._build_nav())
        self.add_stretch(1)
        self._update_nav()

    # ----------------------------------------------------------------- step 1
    def _step_template(self) -> QWidget:
        card = Card(padding=22, spacing=12)
        card.add(SectionHeader("Select a template",
                               subtitle="Choose the layout to generate for every record"))
        self._template_rows: list[OptionRow] = []
        for tpl in self.ctx.services.templates.list_templates():
            icon = "card" if tpl.kind.value == "4×6 Card" else "envelope"
            row = OptionRow(tpl.name, tpl.name,
                            f"{tpl.kind.value} · {tpl.dimensions_label}", icon)
            row.selected.connect(self._pick_template)
            self._template_rows.append(row)
            card.add(row)
        return card

    def _pick_template(self, key: str) -> None:
        self._state["template"] = key
        for row in self._template_rows:
            row.set_active(row._key == key)
        self._update_nav()

    # ----------------------------------------------------------------- step 2
    def _step_profile(self) -> QWidget:
        card = Card(padding=22, spacing=12)
        card.add(SectionHeader("Select a handwriting profile",
                               subtitle="Only ready profiles can be used for generation"))
        self._profile_rows: list[OptionRow] = []
        for prof in self.ctx.services.handwriting.list_profiles():
            subtitle = f"{prof.sample_count} samples · {prof.status.value}"
            row = OptionRow(prof.name, prof.name, subtitle, "handwriting")
            if prof.status.value != "Ready":
                row.setEnabled(False)
            row.selected.connect(self._pick_profile)
            self._profile_rows.append(row)
            card.add(row)
        return card

    def _pick_profile(self, key: str) -> None:
        self._state["profile"] = key
        for row in self._profile_rows:
            row.set_active(row._key == key)
        self._update_nav()

    # ----------------------------------------------------------------- step 3
    def _step_import(self) -> QWidget:
        card = Card(padding=22, spacing=14)
        card.add(SectionHeader("Import data",
                               subtitle="Supported formats: TXT and CSV"))
        self._drop = self._drop_zone()
        card.add(self._drop)

        self._import_stats = QWidget()
        self._import_stats.setVisible(False)
        stats_lay = QVBoxLayout(self._import_stats)
        stats_lay.setContentsMargins(0, 0, 0, 0)
        stats_lay.setSpacing(12)
        self._stats_row = QHBoxLayout()
        stats_lay.addLayout(self._stats_row)
        self._preview_table = DataTable([])
        self._preview_table.setMinimumHeight(220)
        stats_lay.addWidget(self._preview_table)
        card.add(self._import_stats)
        return card

    def _drop_zone(self) -> QFrame:
        p = theme.palette
        f = QFrame()
        f.setObjectName("Drop")
        f.setCursor(Qt.PointingHandCursor)
        f.setStyleSheet(
            f"QFrame#Drop {{ background: {p.surface_alt}; border: 1.5px dashed {p.border_strong};"
            " border-radius: 2px; }"
            f"QFrame#Drop:hover {{ border-color: {p.accent}; background: {p.accent_soft}; }}")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(24, 28, 24, 28)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        ic = label("")
        ic.setPixmap(icons.pixmap("upload", p.accent, 28))
        ic.setAlignment(Qt.AlignCenter)
        lay.addWidget(ic, alignment=Qt.AlignCenter)
        t = label("Drop a TXT or CSV file here, or click to browse", "secondary")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)
        lay.addWidget(label("Up to 5,000 records recommended per batch", "muted"),
                      alignment=Qt.AlignCenter)
        f.mousePressEvent = lambda e: self._do_import()  # type: ignore
        return f

    def _do_import(self) -> None:
        summary = self.ctx.services.imports.preview("members_october.csv")
        self._state["import"] = summary
        self._import_stats.setVisible(True)
        # stats
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        stats = [
            ("File", summary.filename, "neutral"),
            ("Detected", str(summary.records_detected), "neutral"),
            ("Valid", str(summary.valid_records), "success"),
            ("Invalid", str(summary.invalid_records), "warning"),
        ]
        for name, value, tone in stats:
            self._stats_row.addWidget(self._stat_chip(name, value, tone))
        self._stats_row.addStretch(1)
        # table
        self._preview_table.setColumnCount(len(summary.columns))
        self._preview_table.setHorizontalHeaderLabels(summary.columns)
        self._preview_table.setRowCount(0)
        for r in summary.rows:
            self._preview_table.add_row([r.get(c, "") for c in summary.columns])
        self._preview_table.set_stretch(
            {i: QHeaderView.Stretch for i in range(len(summary.columns))})
        self.ctx.toast(f"Imported {summary.valid_records} valid records", "success")
        self._update_nav()

    def _stat_chip(self, name: str, value: str, tone: str) -> QWidget:
        p = theme.palette
        fg = {"success": p.success, "warning": p.warning, "neutral": p.text}.get(tone, p.text)
        w = QFrame()
        w.setStyleSheet(f"background: {p.surface_alt}; border: 1px solid {p.border};"
                        " border-radius: 2px;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 8, 18, 8)
        lay.setSpacing(0)
        v = label(value, "subtitle")
        v.setStyleSheet(f"color: {fg}; font-weight: 700;")
        v.setWordWrap(False)
        lay.addWidget(v)
        lay.addWidget(label(name, "caption"))
        return w

    # ----------------------------------------------------------------- step 4
    def _step_output(self) -> QWidget:
        card = Card(padding=22, spacing=16)
        card.add(SectionHeader("Configure output"))

        row1 = QHBoxLayout()
        row1.setSpacing(14)
        fmt = Select(["PDF", "PNG", "Combined PDF"])
        fmt.currentTextChanged.connect(lambda t: self._state.update(format=t))
        row1.addWidget(Field("Output format", fmt))
        quality = Select(["Draft · 150 dpi", "Standard · 300 dpi", "High · 600 dpi"])
        quality.setCurrentIndex(1)
        quality.currentTextChanged.connect(lambda t: self._state.update(quality=t))
        row1.addWidget(Field("Quality / resolution", quality))
        card.add_layout(row1)

        out_dir = QLineEdit(self._state["output_dir"])
        out_dir.textChanged.connect(lambda t: self._state.update(output_dir=t))
        out_dir.addAction(icons.icon("folder", theme.palette.text_muted, 16),
                          QLineEdit.TrailingPosition)
        card.add(Field("Output directory", out_dir))

        naming = QLineEdit(self._state["naming"])
        naming.textChanged.connect(lambda t: self._state.update(naming=t))
        card.add(Field("File naming pattern", naming,
                       help_text="Available tokens: {index}, {first_name}, {last_name}, {date}"))

        card.add(hline())
        card.add(self._toggle_row("Individual files", "One output file per record",
                                  "individual", True))
        card.add(self._toggle_row("Combined PDF", "Also produce a single merged PDF",
                                  "combined", False))
        card.add(self._toggle_row("Include envelope", "Generate a matching #10 envelope per record",
                                  "envelope", False))
        return card

    def _toggle_row(self, title: str, subtitle: str, key: str, default: bool) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = label(title, "body")
        t.setStyleSheet("font-weight: 600;")
        t.setWordWrap(False)
        col.addWidget(t)
        col.addWidget(label(subtitle, "muted"))
        lay.addLayout(col, stretch=1)
        toggle = ToggleSwitch(default)
        toggle.toggled.connect(lambda on, k=key: self._state.update({k: on}))
        lay.addWidget(toggle)
        return w

    # ----------------------------------------------------------------- step 5
    def _build_review(self) -> None:
        while self._review_layout.count():
            item = self._review_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._review_summary(), stretch=3)
        row.addWidget(self._review_samples(), stretch=2)
        wrap = QWidget()
        wrap.setLayout(row)
        self._review_layout.addWidget(wrap)

    def _review_summary(self) -> Card:
        card = Card(padding=22, spacing=12)
        card.add(SectionHeader("Review & confirm"))
        s = self._state
        records = s["import"].valid_records if s["import"] else 0
        rows = [
            ("Template", s["template"] or "—", "templates"),
            ("Handwriting", s["profile"] or "—", "handwriting"),
            ("Records", f"{records} valid", "database"),
            ("Format", s["format"], "documents"),
            ("Quality", s["quality"], "sparkle"),
            ("Output", s["output_dir"], "folder"),
            ("Naming", s["naming"], "text"),
        ]
        for i, (name, value, icon_name) in enumerate(rows):
            card.add(self._summary_row(name, value, icon_name))
            if i < len(rows) - 1:
                card.add(hline())
        extras = []
        if s["individual"]:
            extras.append("Individual files")
        if s["combined"]:
            extras.append("Combined PDF")
        if s["envelope"]:
            extras.append("Envelope")
        card.add(hline())
        chips = QHBoxLayout()
        chips.setSpacing(8)
        for e in extras or ["Individual files"]:
            chips.addWidget(Badge(e, "accent", dot=False))
        chips.addStretch(1)
        card.add_layout(chips)
        return card

    def _summary_row(self, name: str, value: str, icon_name: str) -> QWidget:
        p = theme.palette
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(12)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, p.text_muted, 17))
        ic.setFixedSize(17, 17)
        lay.addWidget(ic)
        lay.addWidget(label(name, "secondary"))
        lay.addStretch(1)
        v = label(value, "body")
        v.setStyleSheet("font-weight: 600;")
        v.setWordWrap(False)
        lay.addWidget(v)
        return w

    def _review_samples(self) -> Card:
        card = Card(padding=18, spacing=10)
        card.add(SectionHeader("Sample previews"))
        tpl = next((t for t in self.ctx.services.templates.list_templates()
                    if t.name == self._state["template"]), None)
        if tpl is None:
            tpl = self.ctx.services.templates.list_templates()[0]
        for _ in range(1):
            canvas = DocumentCanvas(tpl.width_in, tpl.height_in, tpl.elements,
                                    selectable=False, margin_in=tpl.margin_in)
            canvas.set_safe_area(False)
            canvas.setFixedHeight(190)
            canvas.set_zoom(190 / (tpl.height_in * 96) * 0.82)
            card.add(canvas)
        card.add(label("First 1 of the batch shown. Generation renders every record.", "muted"))
        return card

    # -------------------------------------------------------------------- nav
    def _build_nav(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self._back = Button("Back", variant="secondary", icon_name="arrow-left")
        self._back.clicked.connect(self._go_back)
        lay.addWidget(self._back)
        lay.addStretch(1)
        self._step_label = label("", "muted")
        lay.addWidget(self._step_label)
        self._next = Button("Continue", variant="primary", icon_name="arrow-right")
        self._next.clicked.connect(self._go_next)
        lay.addWidget(self._next)
        return w

    def _can_advance(self) -> bool:
        if self._step == 0:
            return self._state["template"] is not None
        if self._step == 1:
            return self._state["profile"] is not None
        if self._step == 2:
            return self._state["import"] is not None
        return True

    def _update_nav(self) -> None:
        self._stepper.set_current(self._step)
        self._back.setVisible(self._step > 0)
        self._step_label.setText(f"Step {self._step + 1} of {len(STEPS)}")
        last = self._step == len(STEPS) - 1
        if last:
            self._next.setText("Start Generation")
            self._next.setProperty("variant", "primary")
        else:
            self._next.setText("Continue")
        self._next.setEnabled(self._can_advance())

    def _go_next(self) -> None:
        if self._step == len(STEPS) - 1:
            self._start()
            return
        if not self._can_advance():
            self.ctx.toast("Please complete this step first", "warning")
            return
        self._step += 1
        if self._step == len(STEPS) - 1:
            self._build_review()
        self._stack.setCurrentIndex(self._step)
        self._update_nav()

    def _go_back(self) -> None:
        self._step = max(0, self._step - 1)
        self._stack.setCurrentIndex(self._step)
        self._update_nav()

    def _start(self) -> None:
        s = self._state
        records = s["import"].valid_records if s["import"] else 250
        self.ctx.navigate("batch_progress", config={
            "name": "New Batch",
            "template": s["template"], "profile": s["profile"],
            "total": records, "format": s["format"], "output_dir": s["output_dir"],
        })
