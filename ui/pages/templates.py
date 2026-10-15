"""Templates — a responsive grid of template cards with schematic previews."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from models.domain import ElementType, Template
from ui.app_context import AppContext
from ui.components import (
    Button,
    FlowLayout,
    IconButton,
    PageHeader,
    SegmentedControl,
    confirm,
    context_menu,
    label,
    status_badge,
)
from ui.pages.base import ContentPage
from ui.theme import theme


def _fmt(dt: datetime) -> str:
    return f"{dt.strftime('%b')} {dt.day}"


class _TemplateThumb(QWidget):
    """A schematic wireframe preview of a template layout."""

    def __init__(self, template: Template, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tpl = template
        self.setFixedHeight(146)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(p.surface_alt))

        tpl = self._tpl
        pad = 16
        avail_w = self.width() - 2 * pad
        avail_h = self.height() - 2 * pad
        scale = min(avail_w / tpl.width_in, avail_h / tpl.height_in)
        pw = tpl.width_in * scale
        ph = tpl.height_in * scale
        px = (self.width() - pw) / 2
        py = (self.height() - ph) / 2
        paper = QRectF(px, py, pw, ph)

        painter.setBrush(QColor(p.paper))
        painter.setPen(QPen(QColor(p.paper_line), 1))
        painter.drawRect(paper)

        for el in tpl.elements:
            if not el.visible:
                continue
            r = QRectF(px + el.x * scale, py + el.y * scale,
                       max(4, el.width * scale), max(3, el.height * scale))
            if el.type == ElementType.DIVIDER:
                painter.setPen(QPen(QColor(p.border_strong), 1))
                mid = r.center().y()
                painter.drawLine(int(r.left()), int(mid), int(r.right()), int(mid))
                continue
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(p.accent if el.type == ElementType.DATA_FIELD
                                    else p.border_strong))
            # draw a few "text lines"
            line_h = max(2.0, r.height() / 4)
            y = r.top()
            widths = [1.0, 0.8, 0.6]
            i = 0
            while y < r.bottom() - 1 and i < 4:
                lw = r.width() * widths[i % len(widths)]
                painter.drawRoundedRect(QRectF(r.left(), y, lw, min(line_h * 0.6, 3)), 1, 1)
                y += line_h
                i += 1
        painter.end()


class TemplateCard(QFrame):
    open_requested = Signal(str)
    menu_requested = Signal(object, QWidget)
    use_requested = Signal(str)

    def __init__(self, template: Template, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tpl = template
        self.setObjectName("Card")
        self.setFixedWidth(272)
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        thumb = _TemplateThumb(template)
        thumb.setStyleSheet("border-top-left-radius: 2px; border-top-right-radius: 2px;")
        lay.addWidget(thumb)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 14, 12, 14)
        bl.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        name = label(template.name, "body")
        name.setStyleSheet("font-weight: 600;")
        name.setWordWrap(False)
        top.addWidget(name)
        top.addStretch(1)
        top.addWidget(status_badge(template.status.value))
        bl.addLayout(top)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        meta.addWidget(label(template.kind.value, "muted"))
        meta.addWidget(label("·", "muted"))
        meta.addWidget(label(template.dimensions_label, "muted"))
        meta.addStretch(1)
        bl.addLayout(meta)
        bl.addWidget(label(f"Edited {_fmt(template.modified)}", "caption"))

        footer = QHBoxLayout()
        footer.setSpacing(8)
        use = Button("Use Template", variant="soft", size="sm", icon_name="arrow-right")
        use.clicked.connect(lambda: self.use_requested.emit(template.id))
        footer.addWidget(use)
        footer.addStretch(1)
        more = IconButton("more-v", tooltip="Actions", size=30)
        more.clicked.connect(lambda: self.menu_requested.emit(template, more))
        footer.addWidget(more)
        bl.addLayout(footer)
        lay.addWidget(body)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.open_requested.emit(self._tpl.id)


class TemplatesPage(ContentPage):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__(ctx)
        self._filter = 0

        header = PageHeader("Templates", "Reusable layouts for 4×6 cards and #10 envelopes.")
        create = Button("Create Template", variant="primary", icon_name="plus")
        create.clicked.connect(lambda: self.ctx.navigate("template_editor", template_id=None))
        header.add_action(create)
        self.add(header)

        bar = QHBoxLayout()
        self._seg = SegmentedControl(["All", "4×6 Cards", "#10 Envelopes"])
        self._seg.changed.connect(self._on_filter)
        bar.addWidget(self._seg)
        bar.addStretch(1)
        self.add_layout(bar)

        self._grid_host = QWidget()
        self._flow = FlowLayout(self._grid_host, h_spacing=16, v_spacing=16)
        self.add(self._grid_host)
        self.add_stretch(1)
        self._refresh()

    def on_show(self) -> None:
        self._refresh()

    def _on_filter(self, index: int) -> None:
        self._filter = index
        self._refresh()

    def _refresh(self) -> None:
        while self._flow.count():
            item = self._flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        templates = self.ctx.services.templates.list_templates()
        if self._filter == 1:
            templates = [t for t in templates if t.kind.value == "4×6 Card"]
        elif self._filter == 2:
            templates = [t for t in templates if t.kind.value == "#10 Envelope"]
        for tpl in templates:
            card = TemplateCard(tpl)
            card.open_requested.connect(
                lambda tid: self.ctx.navigate("template_editor", template_id=tid))
            card.use_requested.connect(self._use)
            card.menu_requested.connect(self._menu)
            self._flow.addWidget(card)

    def _use(self, template_id: str) -> None:
        self.ctx.navigate("document_editor", document_id=None, template_id=template_id)

    def _menu(self, template, anchor: QWidget) -> None:
        menu = context_menu(self, [
            ("Edit", "edit", lambda: self.ctx.navigate("template_editor", template_id=template.id)),
            ("Duplicate", "duplicate", lambda: self._duplicate(template)),
            ("Rename", "text", lambda: self.ctx.toast("Rename — coming soon", "info")),
            ("Use Template", "arrow-right", lambda: self._use(template.id)),
            ("-", "", None),
            ("!Delete", "trash", lambda: self._delete(template)),
        ])
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomRight()))

    def _duplicate(self, template) -> None:
        self.ctx.services.templates.duplicate_template(template.id)
        self.ctx.toast(f"Duplicated “{template.name}”", "success")
        self._refresh()

    def _delete(self, template) -> None:
        if confirm(self, "Delete template?",
                   f"“{template.name}” will be removed. Documents already created keep their layout.",
                   confirm_text="Delete", destructive=True):
            self.ctx.services.templates.delete_template(template.id)
            self.ctx.toast("Template deleted", "success")
            self._refresh()
