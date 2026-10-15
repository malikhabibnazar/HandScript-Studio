"""Handwriting Profile Detail — overview, samples, analysis and live preview."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from models.domain import ProfileStatus
from ui.app_context import AppContext
from ui.components import (
    Avatar,
    Button,
    Card,
    EmptyState,
    ErrorState,
    IconButton,
    PageHeader,
    SectionHeader,
    SegmentedControl,
    Spinner,
    hline,
    label,
    status_badge,
)
from ui.components.common import spacer
from ui.pages.base import ContentPage
from ui.pages.documents import fmt_date
from ui.theme import icons, theme


class _PreviewCanvas(QWidget):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._variation = 2
        self.setMinimumHeight(150)

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def set_variation(self, v: int) -> None:
        self._variation = v
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.fillRect(self.rect(), QColor(p.paper))
        # ruled lines
        painter.setPen(QColor(p.grid))
        gap = 38
        y = 44
        while y < self.height():
            painter.drawLine(24, y, self.width() - 24, y)
            y += gap
        f = QFont(theme.type.handwriting)
        f.setPixelSize(28)
        # variation nudges slant + size slightly
        f.setItalic(self._variation % 2 == 0)
        painter.setFont(f)
        painter.setPen(QColor(0x1E, 0x1E, 0x24))
        painter.drawText(self.rect().adjusted(28, 8, -28, -8),
                         Qt.TextWordWrap | Qt.AlignTop | Qt.AlignLeft,
                         self._text or "Type something to preview…")
        painter.end()


class HandwritingDetailPage(ContentPage):
    def __init__(self, ctx: AppContext, *, profile_id: str | None = None) -> None:
        super().__init__(ctx)
        self._profile = ctx.services.handwriting.get_profile(profile_id)
        if not self._profile:
            self.add(EmptyState("Profile not found", "This profile may have been deleted.",
                                icon_name="handwriting", action="Back to profiles"))
            self.body.itemAt(0).widget().action_button.clicked.connect(
                lambda: self.ctx.navigate("handwriting"))
            self.add_stretch(1)
            return

        self._build_header()
        self._build_overview()

        row = QHBoxLayout()
        row.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)
        left.addWidget(self._build_samples())
        left.addWidget(self._build_preview())
        row.addLayout(left, stretch=3)
        row.addWidget(self._build_analysis(), stretch=2)
        self.add_layout(row)
        self.add_stretch(1)

    def _build_header(self) -> None:
        prof = self._profile
        header = PageHeader(prof.name, prof.description,
                            breadcrumb=["Handwriting", prof.name])
        if header.breadcrumb:
            header.breadcrumb.navigate.connect(lambda i: self.ctx.navigate("handwriting"))
        if not prof.is_default:
            default_btn = Button("Set as Default", variant="secondary", icon_name="star")
            default_btn.clicked.connect(self._set_default)
            header.add_action(default_btn)
        add = Button("Add Sample", variant="primary", icon_name="plus")
        add.clicked.connect(lambda: self.ctx.toast("Add samples via file picker", "info"))
        header.add_action(add)
        self.add(header)

    def _build_overview(self) -> None:
        prof = self._profile
        card = Card(padding=18, spacing=0)
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(Avatar(prof.name, 52))
        col = QVBoxLayout()
        col.setSpacing(3)
        name = label(prof.name, "subtitle")
        name.setWordWrap(False)
        col.addWidget(name)
        col.addWidget(label(f"Created {fmt_date(prof.created)} · {prof.sample_count} samples",
                            "muted"))
        row.addLayout(col)
        row.addStretch(1)
        row.addWidget(status_badge(prof.status.value))
        card.add_layout(row)
        self.add(card)

    def _build_samples(self) -> Card:
        card = Card(padding=20, spacing=14)
        card.add(SectionHeader(
            "Samples", subtitle=f"{self._profile.sample_count} handwriting samples"))
        grid = QGridLayout()
        grid.setSpacing(12)
        samples = self._profile.samples
        cols = 4
        for i, sample in enumerate(samples[:8]):
            grid.addWidget(self._sample_thumb(sample), i // cols, i % cols)
        # add-sample tile
        add_tile = self._add_sample_tile()
        pos = len(samples[:8])
        grid.addWidget(add_tile, pos // cols, pos % cols)
        card.add_layout(grid)
        return card

    def _sample_thumb(self, sample) -> QWidget:
        p = theme.palette
        w = QWidget()
        w.setFixedHeight(104)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        thumb = QWidget()
        thumb.setFixedHeight(72)
        thumb.setStyleSheet(
            f"background: {p.surface_alt}; border: 1px solid {p.border}; border-radius: 2px;")
        tl = QVBoxLayout(thumb)
        tl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap("image", p.text_muted, 20))
        ic.setAlignment(Qt.AlignCenter)
        tl.addWidget(ic)
        lay.addWidget(thumb)
        meta = QHBoxLayout()
        meta.setSpacing(4)
        fn = label(sample.filename, "caption")
        fn.setWordWrap(False)
        meta.addWidget(fn)
        meta.addStretch(1)
        q = label(f"{sample.quality}%", "caption")
        q.setStyleSheet(f"color: {p.success if sample.quality >= 75 else p.warning};"
                        " font-weight: 600;")
        meta.addWidget(q)
        lay.addLayout(meta)
        return w

    def _add_sample_tile(self) -> QWidget:
        p = theme.palette
        w = QWidget()
        w.setFixedHeight(104)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        tile = QWidget()
        tile.setFixedHeight(72)
        tile.setCursor(Qt.PointingHandCursor)
        tile.setStyleSheet(
            f"background: transparent; border: 1px dashed {p.border_strong}; border-radius: 2px;")
        tl = QVBoxLayout(tile)
        tl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap("plus", p.accent, 20))
        ic.setAlignment(Qt.AlignCenter)
        tl.addWidget(ic)
        tile.mousePressEvent = lambda e: self.ctx.toast("Choose image samples…", "info")  # type: ignore
        lay.addWidget(tile)
        lay.addWidget(label("Add sample", "caption"))
        return w

    def _build_analysis(self) -> Card:
        card = Card(padding=20, spacing=14)
        prof = self._profile
        card.add(SectionHeader("Analysis", subtitle="Returned by the local engine"))

        if prof.status == ProfileStatus.PROCESSING:
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(0, 20, 0, 20)
            bl.setSpacing(12)
            bl.setAlignment(Qt.AlignCenter)
            bl.addWidget(Spinner(30), alignment=Qt.AlignCenter)
            t = label("Analysing samples…", "secondary")
            t.setAlignment(Qt.AlignCenter)
            bl.addWidget(t)
            bl.addWidget(label("This usually takes a few moments.", "muted"),
                         alignment=Qt.AlignCenter)
            card.add(box)
            return card

        if prof.analysis is None or prof.status == ProfileStatus.ERROR:
            err = ErrorState(
                "Analysis failed",
                "The engine couldn't analyse these samples. Try replacing low-quality samples.",
                action="Re-run analysis")
            err.action_button.clicked.connect(
                lambda: self.ctx.toast("Re-running analysis…", "info"))
            card.add(err)
            return card

        a = prof.analysis
        status_tone = "warning" if prof.status == ProfileStatus.NEEDS_REVIEW else "success"
        head = QHBoxLayout()
        head.addWidget(label("Analysis status", "secondary"))
        head.addStretch(1)
        head.addWidget(status_badge(prof.status.value))
        card.add_layout(head)
        card.add(hline())

        card.add(self._metric_bar("Character coverage", a.character_coverage, status_tone))
        card.add(self._metric_bar("Sample quality", a.sample_quality, "success"))
        card.add(self._metric_bar("Baseline stability", a.baseline_stability, "success"))
        card.add(self._metric_bar("Spacing consistency", a.spacing_consistency, status_tone))

        facts = QGridLayout()
        facts.setHorizontalSpacing(16)
        facts.setVerticalSpacing(8)
        self._fact(facts, 0, "Samples analysed", str(a.samples_analyzed))
        self._fact(facts, 1, "Avg stroke width", f"{a.avg_stroke_width:g} mm")
        self._fact(facts, 2, "Slant", f"{a.slant_degrees:g}°")
        card.add_layout(facts)

        if a.notes:
            card.add(hline())
            for note in a.notes:
                card.add(self._note(note))
        return card

    def _metric_bar(self, name: str, value: int, tone: str) -> QWidget:
        p = theme.palette
        color = {"success": p.success, "warning": p.warning, "danger": p.danger}.get(tone, p.accent)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        row = QHBoxLayout()
        row.addWidget(label(name, "secondary"))
        row.addStretch(1)
        val = label(f"{value}%", "secondary")
        val.setStyleSheet(f"color: {color}; font-weight: 700;")
        val.setWordWrap(False)
        row.addWidget(val)
        lay.addLayout(row)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(value)
        bar.setTextVisible(False)
        bar.setStyleSheet(
            f"QProgressBar {{ background: {p.neutral_soft}; border-radius: 2px; height: 7px; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}")
        lay.addWidget(bar)
        return w

    def _fact(self, grid: QGridLayout, col: int, name: str, value: str) -> None:
        box = QVBoxLayout()
        box.setSpacing(1)
        v = label(value, "body")
        v.setStyleSheet("font-weight: 700;")
        v.setWordWrap(False)
        box.addWidget(v)
        box.addWidget(label(name, "caption"))
        grid.addLayout(box, 0, col)

    def _note(self, text: str) -> QWidget:
        p = theme.palette
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(8)
        ic = label("")
        ic.setPixmap(icons.pixmap("info", p.text_muted, 15))
        ic.setFixedSize(15, 15)
        lay.addWidget(ic, alignment=Qt.AlignTop)
        lay.addWidget(label(text, "muted"), stretch=1)
        return w

    def _build_preview(self) -> Card:
        card = Card(padding=20, spacing=12)
        trailing = Button("Refresh Preview", variant="soft", size="sm", icon_name="refresh")
        card.add(SectionHeader("Rendering preview", trailing=trailing))

        self._preview_input = QLineEdit("The quick brown fox jumps over the lazy dog.")
        self._preview_input.textChanged.connect(
            lambda t: self._preview.set_text(t))
        card.add(self._preview_input)

        self._preview = _PreviewCanvas(self._preview_input.text())
        self._preview.setStyleSheet(
            f"border: 1px solid {theme.palette.border}; border-radius: 2px;")
        card.add(self._preview)

        controls = QHBoxLayout()
        controls.addWidget(label("Variation", "secondary"))
        controls.addSpacing(10)
        seg = SegmentedControl(["1", "2", "3", "4", "5"])
        seg.set_current(1)
        seg.changed.connect(lambda i: self._preview.set_variation(i + 1))
        controls.addWidget(seg)
        controls.addStretch(1)
        card.add_layout(controls)

        trailing.clicked.connect(lambda: (self._preview.update(),
                                          self.ctx.toast("Preview refreshed", "info")))
        return card

    def _set_default(self) -> None:
        self.ctx.services.handwriting.set_default(self._profile.id)
        self.ctx.toast(f"“{self._profile.name}” is now the default", "success")
