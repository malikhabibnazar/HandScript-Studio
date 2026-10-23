"""Template Editor — visual layout editor with an element toolbox."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.domain import ElementType, Template, TemplateElement, TemplateKind, TemplateStatus
from ui.app_context import AppContext
from ui.components import (
    Breadcrumb,
    Button,
    Field,
    IconButton,
    SegmentedControl,
    Select,
    ToggleSwitch,
    confirm,
    hline,
    label,
)
from ui.components.canvas import DocumentCanvas
from ui.theme import icons, theme
from datetime import datetime

TOOLBOX = [
    (ElementType.TEXT, "Text", "text"),
    (ElementType.ADDRESS, "Address", "envelope"),
    (ElementType.DATA_FIELD, "Data Field", "database"),
    (ElementType.DIVIDER, "Divider", "align-center"),
    (ElementType.IMAGE, "Image / Logo", "image"),
]


class TemplateEditorPage(QWidget):
    def __init__(self, ctx: AppContext, *, template_id: str | None = None) -> None:
        super().__init__()
        self.ctx = ctx
        existing = ctx.services.templates.get_template(template_id) if template_id else None
        if existing:
            self._template = copy.deepcopy(existing)
        else:
            self._template = Template(
                id="tpl-new", name="Untitled Template", kind=TemplateKind.CARD_4X6,
                width_in=6.0, height_in=4.0, status=TemplateStatus.DRAFT,
                modified=datetime.now(), elements=[], margin_in=0.2)
        self._elements = self._template.elements
        self._selected: TemplateElement | None = None
        self._counter = len(self._elements)
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())
        root.addWidget(hline())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_center())
        splitter.addWidget(self._build_right())
        splitter.setSizes([260, 780, 300])
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)
        root.addWidget(hline())
        root.addWidget(self._build_bottom())
        self._show_empty_inspector()

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 14, 20, 12)
        col = QVBoxLayout()
        col.setSpacing(4)
        crumb = Breadcrumb(["Templates", "Editor"])
        crumb.navigate.connect(lambda i: self.ctx.navigate("templates"))
        col.addWidget(crumb)
        t = label(self._template.name, "titleSm")
        t.setWordWrap(False)
        col.addWidget(t)
        lay.addLayout(col)
        lay.addStretch(1)
        return bar

    def _panel(self) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("EditorPanel")
        frame.setStyleSheet(f"QFrame#EditorPanel {{ background: {theme.palette.surface}; }}")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        return frame, lay

    def _panel_header(self, title: str, subtitle: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 12)
        lay.setSpacing(1)
        tl = label(title, "subtitle")
        tl.setWordWrap(False)
        lay.addWidget(tl)
        lay.addWidget(label(subtitle, "muted"))
        return w

    # ---------------------------------------------------------------- left panel
    def _build_left(self) -> QWidget:
        frame, lay = self._panel()
        frame.setMinimumWidth(230)
        lay.addWidget(self._panel_header("Elements", "Drag-free: click to add"))
        lay.addWidget(hline())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(8)

        for etype, text, icon_name in TOOLBOX:
            box.addWidget(self._tool_button(etype, text, icon_name))

        box.addSpacing(10)
        box.addWidget(label("CANVAS", "section"))
        name = QLineEdit(self._template.name)
        name.textChanged.connect(lambda t: setattr(self._template, "name", t))
        box.addWidget(Field("Template name", name))

        kind = SegmentedControl(["4×6 Card", "#10 Envelope"])
        kind.set_current(0 if self._template.kind == TemplateKind.CARD_4X6 else 1)
        kind.changed.connect(self._change_kind)
        box.addWidget(Field("Type", kind))

        dims = QHBoxLayout()
        self._w_spin = self._mk_dspin(self._template.width_in)
        self._w_spin.valueChanged.connect(self._change_dims)
        self._h_spin = self._mk_dspin(self._template.height_in)
        self._h_spin.valueChanged.connect(self._change_dims)
        dims.addWidget(Field("Width", self._w_spin))
        dims.addWidget(Field("Height", self._h_spin))
        box.addLayout(dims)

        margin = self._mk_dspin(self._template.margin_in)
        margin.valueChanged.connect(lambda v: (setattr(self._template, "margin_in", v),
                                               setattr(self._canvas, "_margin_in", v),
                                               self._canvas.update()))
        box.addWidget(Field("Margins", margin))
        box.addStretch(1)
        scroll.setWidget(content)
        lay.addWidget(scroll, stretch=1)
        return frame

    def _tool_button(self, etype: ElementType, text: str, icon_name: str) -> QFrame:
        p = theme.palette
        f = QFrame()
        f.setObjectName("Tool")
        f.setCursor(Qt.PointingHandCursor)
        f.setStyleSheet(
            "QFrame#Tool { background: transparent; border: 1px solid " + p.border +
            "; border-radius: 2px; }"
            "QFrame#Tool:hover { border-color: " + p.accent + "; background: " + p.accent_soft + "; }")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(10)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, p.text_secondary, 18))
        ic.setFixedSize(18, 18)
        lay.addWidget(ic)
        lbl = label(text, "body")
        lbl.setWordWrap(False)
        lbl.setStyleSheet("font-weight: 600;")
        lay.addWidget(lbl)
        lay.addStretch(1)
        plus = label("")
        plus.setPixmap(icons.pixmap("plus", p.text_muted, 15))
        lay.addWidget(plus)
        f.mousePressEvent = lambda e, t=etype: self._add_element(t)  # type: ignore
        return f

    def _mk_dspin(self, value: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(0.0, 20.0)
        s.setSingleStep(0.1)
        s.setDecimals(2)
        s.setSuffix(" in")
        s.setValue(value)
        return s

    # --------------------------------------------------------------- center panel
    def _build_center(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_canvas_toolbar())
        lay.addWidget(hline())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setStyleSheet(f"background: {theme.palette.canvas_bg}; border: none;")
        self._canvas = DocumentCanvas(self._template.width_in, self._template.height_in,
                                      self._elements, margin_in=self._template.margin_in)
        self._canvas.set_grid(True)
        self._canvas.element_selected.connect(self._on_select)
        self._scroll.setWidget(self._canvas)
        lay.addWidget(self._scroll, stretch=1)
        QTimer.singleShot(60, lambda: (self._canvas.fit(self._scroll.viewport().size()),
                                       self._update_zoom()))
        return wrap

    def _build_canvas_toolbar(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(6)
        zo = IconButton("zoom-out", tooltip="Zoom out", size=30)
        zo.clicked.connect(lambda: self._zoom(0.9))
        zi = IconButton("zoom-in", tooltip="Zoom in", size=30)
        zi.clicked.connect(lambda: self._zoom(1.1))
        self._zoom_label = label("100%", "secondary")
        self._zoom_label.setFixedWidth(46)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        fit = Button("Fit", variant="ghost", size="sm")
        fit.clicked.connect(lambda: (self._canvas.fit(self._scroll.viewport().size()),
                                     self._update_zoom()))
        lay.addWidget(zo)
        lay.addWidget(self._zoom_label)
        lay.addWidget(zi)
        lay.addWidget(fit)
        lay.addStretch(1)
        grid = IconButton("grid", tooltip="Toggle grid", size=30, checkable=True)
        grid.setChecked(True)
        grid.toggled.connect(lambda on: self._canvas.set_grid(on))
        safe = IconButton("card", tooltip="Toggle safe area", size=30, checkable=True)
        safe.setChecked(True)
        safe.toggled.connect(lambda on: self._canvas.set_safe_area(on))
        lay.addWidget(grid)
        lay.addWidget(safe)
        return bar

    def _zoom(self, f: float) -> None:
        self._canvas.set_zoom(self._canvas.zoom() * f)
        self._update_zoom()

    def _update_zoom(self) -> None:
        self._zoom_label.setText(f"{int(self._canvas.zoom() * 100)}%")

    # ---------------------------------------------------------------- right panel
    def _build_right(self) -> QWidget:
        frame, lay = self._panel()
        frame.setMinimumWidth(260)
        lay.addWidget(self._panel_header("Properties", "Inspector"))
        lay.addWidget(hline())
        self._stack = QStackedWidget()
        lay.addWidget(self._stack, stretch=1)

        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setContentsMargins(24, 40, 24, 24)
        el.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        hint = label("Add an element from the toolbox, or select one on the canvas to edit it.",
                     "muted")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        el.addWidget(hint)
        self._stack.addWidget(empty)
        self._stack.addWidget(self._build_form())
        return frame

    def _build_form(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        form = QVBoxLayout(content)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(14)

        self._f_name = label("Element", "secondary")
        self._f_name.setStyleSheet("font-weight: 600;")
        form.addWidget(self._f_name)
        form.addWidget(hline())

        self._f_content = QPlainTextEdit()
        self._f_content.setFixedHeight(80)
        self._f_content.textChanged.connect(self._apply_content)
        form.addWidget(Field("Content", self._f_content,
                             help_text="Use {placeholders} for data fields."))

        self._f_size = QSpinBox()
        self._f_size.setRange(6, 96)
        self._f_size.valueChanged.connect(self._apply_size)
        form.addWidget(Field("Font size", self._f_size))

        pos = QHBoxLayout()
        self._f_x = self._mk_dspin(0)
        self._f_x.valueChanged.connect(self._apply_geom)
        self._f_y = self._mk_dspin(0)
        self._f_y.valueChanged.connect(self._apply_geom)
        pos.addWidget(Field("X", self._f_x))
        pos.addWidget(Field("Y", self._f_y))
        form.addLayout(pos)

        size = QHBoxLayout()
        self._f_w = self._mk_dspin(0)
        self._f_w.valueChanged.connect(self._apply_geom)
        self._f_h = self._mk_dspin(0)
        self._f_h.valueChanged.connect(self._apply_geom)
        size.addWidget(Field("Width", self._f_w))
        size.addWidget(Field("Height", self._f_h))
        form.addLayout(size)

        self._f_align = SegmentedControl(["Left", "Center", "Right"])
        self._f_align.changed.connect(self._apply_align)
        form.addWidget(Field("Alignment", self._f_align))

        vis = QHBoxLayout()
        vis.addWidget(label("Visible", "secondary"))
        vis.addStretch(1)
        self._f_visible = ToggleSwitch(True)
        self._f_visible.toggled.connect(self._apply_visible)
        vis.addWidget(self._f_visible)
        form.addLayout(vis)

        form.addSpacing(6)
        delete = Button("Delete element", variant="dangerGhost", icon_name="trash", size="sm")
        delete.clicked.connect(self._delete_selected)
        form.addWidget(delete)
        form.addStretch(1)
        scroll.setWidget(content)
        return scroll

    # ----------------------------------------------------------------- bottom bar
    def _build_bottom(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("EditorBottomBar")
        bar.setStyleSheet(f"QFrame#EditorBottomBar {{ background: {theme.palette.surface}; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(10)
        self._count_label = label("", "muted")
        self._update_count()
        lay.addWidget(self._count_label)
        lay.addStretch(1)
        cancel = Button("Cancel", variant="ghost")
        cancel.clicked.connect(lambda: self.ctx.navigate("templates"))
        preview = Button("Preview", variant="secondary", icon_name="eye")
        preview.clicked.connect(lambda: self.ctx.toast("Previewing template…", "info"))
        save = Button("Save Template", variant="primary", icon_name="check")
        save.clicked.connect(self._save)
        for b in (cancel, preview, save):
            lay.addWidget(b)
        return bar

    # ------------------------------------------------------------------ behavior
    def _add_element(self, etype: ElementType) -> None:
        self._counter += 1
        defaults = {
            ElementType.TEXT: ("New text", 2.0, 16),
            ElementType.ADDRESS: ("{first_name} {last_name}\n{street}\n{city}, {state} {zip}", 1.4, 14),
            ElementType.DATA_FIELD: ("{field_name}", 0.5, 14),
            ElementType.DIVIDER: ("", 0.02, 12),
            ElementType.IMAGE: ("", 1.2, 12),
        }
        content, h, fs = defaults[etype]
        cx = max(0.3, self._template.width_in / 2 - 1.2)
        cy = max(0.3, self._template.height_in / 2 - h / 2)
        el = TemplateElement(
            id=f"el-{self._counter}", type=etype, name=etype.value,
            x=round(cx, 2), y=round(cy, 2), width=2.4, height=h,
            align="left", font_size=fs, content=content, visible=True)
        self._elements.append(el)
        self._canvas.set_elements(self._elements)
        self._canvas.select(el.id)
        self._on_select(el)
        self._update_count()
        self.ctx.toast(f"Added {etype.value.lower()} element", "info")

    def _change_kind(self, index: int) -> None:
        if index == 0:
            self._template.kind = TemplateKind.CARD_4X6
            self._w_spin.setValue(6.0)
            self._h_spin.setValue(4.0)
        else:
            self._template.kind = TemplateKind.ENVELOPE_10
            self._w_spin.setValue(9.5)
            self._h_spin.setValue(4.125)

    def _change_dims(self) -> None:
        self._template.width_in = self._w_spin.value()
        self._template.height_in = self._h_spin.value()
        self._canvas._w_in = self._template.width_in
        self._canvas._h_in = self._template.height_in
        self._canvas.fit(self._scroll.viewport().size())
        self._update_zoom()

    def _on_select(self, element) -> None:
        self._selected = element
        if element is None:
            self._show_empty_inspector()
            return
        self._stack.setCurrentIndex(1)
        self._loading = True
        self._f_name.setText(f"{element.type.value} · {element.name}")
        self._f_content.setPlainText(element.content)
        self._f_size.setValue(element.font_size)
        self._f_x.setValue(element.x)
        self._f_y.setValue(element.y)
        self._f_w.setValue(element.width)
        self._f_h.setValue(element.height)
        self._f_align.set_current({"left": 0, "center": 1, "right": 2}.get(element.align, 0))
        self._f_visible.setChecked(element.visible)
        self._loading = False

    def _show_empty_inspector(self) -> None:
        self._stack.setCurrentIndex(0)

    def _apply_content(self) -> None:
        if self._selected and not self._loading:
            self._selected.content = self._f_content.toPlainText()
            self._canvas.update()

    def _apply_size(self, v: int) -> None:
        if self._selected and not self._loading:
            self._selected.font_size = v
            self._canvas.update()

    def _apply_geom(self) -> None:
        if self._selected and not self._loading:
            self._selected.x = self._f_x.value()
            self._selected.y = self._f_y.value()
            self._selected.width = self._f_w.value()
            self._selected.height = self._f_h.value()
            self._canvas.update()

    def _apply_align(self, index: int) -> None:
        if self._selected and not self._loading:
            self._selected.align = ["left", "center", "right"][index]
            self._canvas.update()

    def _apply_visible(self, on: bool) -> None:
        if self._selected and not self._loading:
            self._selected.visible = on
            self._canvas.update()

    def _delete_selected(self) -> None:
        if not self._selected:
            return
        name = self._selected.name or "This element"
        if not confirm(
            self,
            "Delete element?",
            f"“{name}” will be removed from this template.",
            confirm_text="Delete",
            destructive=True,
        ):
            return
        self._elements.remove(self._selected)
        self._selected = None
        self._canvas.set_elements(self._elements)
        self._canvas.select(None)
        self._show_empty_inspector()
        self._update_count()

    def _update_count(self) -> None:
        self._count_label.setText(
            f"{self._template.kind.value} · {self._template.width_in:g}×{self._template.height_in:g} in"
            f" · {len(self._elements)} elements")

    def _save(self) -> None:
        self.ctx.toast(f"Template “{self._template.name}” saved", "success")
        self.ctx.navigate("templates")
