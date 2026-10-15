"""Document Editor — professional three-panel layout editor."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.domain import ElementType, TemplateElement
from ui.app_context import AppContext
from ui.components import (
    Breadcrumb,
    Button,
    Field,
    IconButton,
    SegmentedControl,
    Select,
    ToggleSwitch,
    hline,
    label,
)
from ui.components.canvas import DocumentCanvas
from ui.theme import icons, theme


class DocumentEditorPage(QWidget):
    def __init__(self, ctx: AppContext, *, document_id: str | None = None,
                 template_id: str | None = None) -> None:
        super().__init__()
        self.ctx = ctx
        self._doc = ctx.services.documents.get_document(document_id) if document_id else None

        templates = ctx.services.templates.list_templates()
        tpl = None
        if template_id:
            tpl = ctx.services.templates.get_template(template_id)
        if tpl is None and self._doc is not None:
            tpl = next((t for t in templates if t.name == self._doc.template), None)
        self._template = tpl or templates[0]
        self._elements: list[TemplateElement] = copy.deepcopy(self._template.elements)
        self._selected: TemplateElement | None = None

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
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([280, 760, 300])
        root.addWidget(splitter, stretch=1)
        root.addWidget(hline())
        root.addWidget(self._build_bottom())

        self._show_empty_inspector()

    # ------------------------------------------------------------------- chrome
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 14, 20, 12)
        lay.setSpacing(14)
        col = QVBoxLayout()
        col.setSpacing(4)
        crumb = Breadcrumb(["Documents", "Editor"])
        crumb.navigate.connect(lambda i: self.ctx.navigate("documents"))
        col.addWidget(crumb)
        title = label(self._doc.name if self._doc else "Untitled Document", "titleSm")
        title.setWordWrap(False)
        col.addWidget(title)
        lay.addLayout(col)
        lay.addStretch(1)
        return bar

    def _panel(self, width: int | None = None) -> tuple[QFrame, QVBoxLayout]:
        p = theme.palette
        frame = QFrame()
        frame.setObjectName("EditorPanel")
        frame.setStyleSheet(f"QFrame#EditorPanel {{ background: {p.surface}; }}")
        if width:
            frame.setFixedWidth(width)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        return frame, lay

    # ---------------------------------------------------------------- left panel
    def _build_left(self) -> QWidget:
        frame, lay = self._panel()
        frame.setMinimumWidth(240)
        lay.addWidget(self._panel_header("Document", "Configuration"))
        lay.addWidget(hline())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        form = QVBoxLayout(content)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(16)

        name = QLineEdit(self._doc.name if self._doc else "Untitled Document")
        form.addWidget(Field("Document name", name))

        tpl_names = [t.name for t in self.ctx.services.templates.list_templates()]
        tpl_select = Select(tpl_names)
        tpl_select.setCurrentText(self._template.name)
        tpl_select.currentTextChanged.connect(self._change_template)
        form.addWidget(Field("Template", tpl_select))

        profiles = [p.name for p in self.ctx.services.handwriting.list_profiles()]
        form.addWidget(Field("Handwriting profile", Select(profiles)))

        form.addWidget(Field("Page size", Select(
            [f"{self._template.kind.value} — {self._template.dimensions_label}",
             "4×6 Card", "#10 Envelope", "Custom…"])))

        orient = SegmentedControl(["Landscape", "Portrait"])
        form.addWidget(Field("Orientation", orient))

        margin = QDoubleSpinBox()
        margin.setRange(0.0, 2.0)
        margin.setSingleStep(0.05)
        margin.setValue(self._template.margin_in)
        margin.setSuffix(" in")
        margin.valueChanged.connect(self._change_margin)
        form.addWidget(Field("Margins", margin))

        form.addWidget(Field("Output format", Select(["PDF", "PNG", "Combined PDF"])))
        form.addStretch(1)

        scroll.setWidget(content)
        lay.addWidget(scroll, stretch=1)
        return frame

    # --------------------------------------------------------------- center panel
    def _build_center(self) -> QWidget:
        p = theme.palette
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._build_canvas_toolbar())
        lay.addWidget(hline())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setStyleSheet(f"background: {p.canvas_bg}; border: none;")
        self._canvas = DocumentCanvas(
            self._template.width_in, self._template.height_in, self._elements,
            margin_in=self._template.margin_in)
        self._canvas.set_safe_area(True)
        self._canvas.element_selected.connect(self._on_canvas_select)
        self._scroll.setWidget(self._canvas)
        lay.addWidget(self._scroll, stretch=1)

        # fit once laid out
        self._canvas.set_zoom(1.0)
        wrap_ref = self

        def _fit_later():
            self._canvas.fit(self._scroll.viewport().size())
            self._update_zoom_label()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(60, _fit_later)
        return wrap

    def _build_canvas_toolbar(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(6)

        zoom_out = IconButton("zoom-out", tooltip="Zoom out", size=30)
        zoom_out.clicked.connect(lambda: self._zoom_by(0.9))
        zoom_in = IconButton("zoom-in", tooltip="Zoom in", size=30)
        zoom_in.clicked.connect(lambda: self._zoom_by(1.1))
        self._zoom_label = label("100%", "secondary")
        self._zoom_label.setFixedWidth(46)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        fit = Button("Fit", variant="ghost", size="sm")
        fit.clicked.connect(self._fit)
        lay.addWidget(zoom_out)
        lay.addWidget(self._zoom_label)
        lay.addWidget(zoom_in)
        lay.addWidget(fit)
        lay.addStretch(1)

        self._grid_btn = IconButton("grid", tooltip="Toggle grid", size=30, checkable=True)
        self._grid_btn.toggled.connect(self._canvas_grid)
        self._ruler_btn = IconButton("ruler", tooltip="Toggle ruler", size=30, checkable=True)
        self._ruler_btn.toggled.connect(lambda on: self._canvas.set_ruler(on))
        self._safe_btn = IconButton("card", tooltip="Toggle print-safe area", size=30, checkable=True)
        self._safe_btn.setChecked(True)
        self._safe_btn.toggled.connect(lambda on: self._canvas.set_safe_area(on))
        lay.addWidget(self._grid_btn)
        lay.addWidget(self._ruler_btn)
        lay.addWidget(self._safe_btn)
        return bar

    def _canvas_grid(self, on: bool) -> None:
        self._canvas.set_grid(on)

    def _zoom_by(self, factor: float) -> None:
        self._canvas.set_zoom(self._canvas.zoom() * factor)
        self._update_zoom_label()

    def _fit(self) -> None:
        self._canvas.fit(self._scroll.viewport().size())
        self._update_zoom_label()

    def _update_zoom_label(self) -> None:
        self._zoom_label.setText(f"{int(self._canvas.zoom() * 100)}%")

    # ---------------------------------------------------------------- right panel
    def _build_right(self) -> QWidget:
        frame, lay = self._panel()
        frame.setMinimumWidth(260)
        lay.addWidget(self._panel_header("Properties", "Inspector"))
        lay.addWidget(hline())

        self._inspector_stack = QStackedWidget()
        lay.addWidget(self._inspector_stack, stretch=1)

        # empty hint
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setContentsMargins(24, 40, 24, 24)
        el.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        icon = label("")
        icon.setPixmap(icons.pixmap("text", theme.palette.text_muted, 26))
        icon.setAlignment(Qt.AlignCenter)
        el.addWidget(icon, alignment=Qt.AlignHCenter)
        hint = label("Select an element on the canvas to edit its properties.", "muted")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        el.addWidget(hint)
        self._inspector_stack.addWidget(empty)

        self._inspector_stack.addWidget(self._build_inspector_form())
        return frame

    def _build_inspector_form(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        form = QVBoxLayout(content)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(15)

        self._f_type = label("Text element", "secondary")
        self._f_type.setStyleSheet("font-weight: 600;")
        form.addWidget(self._f_type)
        form.addWidget(hline())

        self._f_text = QPlainTextEdit()
        self._f_text.setFixedHeight(84)
        self._f_text.textChanged.connect(self._apply_text)
        form.addWidget(Field("Content", self._f_text))

        self._f_profile = Select([p.name for p in self.ctx.services.handwriting.list_profiles()])
        form.addWidget(Field("Handwriting profile", self._f_profile))

        self._f_size = QSpinBox()
        self._f_size.setRange(6, 96)
        self._f_size.valueChanged.connect(self._apply_size)
        form.addWidget(Field("Font size", self._f_size))

        pos_row = QHBoxLayout()
        pos_row.setSpacing(10)
        self._f_x = self._mk_dspin(" in")
        self._f_x.valueChanged.connect(self._apply_pos)
        self._f_y = self._mk_dspin(" in")
        self._f_y.valueChanged.connect(self._apply_pos)
        pos_row.addWidget(Field("X", self._f_x))
        pos_row.addWidget(Field("Y", self._f_y))
        form.addLayout(pos_row)

        size_row = QHBoxLayout()
        size_row.setSpacing(10)
        self._f_w = self._mk_dspin(" in")
        self._f_w.valueChanged.connect(self._apply_pos)
        self._f_h = self._mk_dspin(" in")
        self._f_h.valueChanged.connect(self._apply_pos)
        size_row.addWidget(Field("Width", self._f_w))
        size_row.addWidget(Field("Height", self._f_h))
        form.addLayout(size_row)

        self._f_align = SegmentedControl(["Left", "Center", "Right"])
        self._f_align.changed.connect(self._apply_align)
        form.addWidget(Field("Alignment", self._f_align))

        self._f_line = self._mk_slider(80, 240, 120)
        form.addWidget(Field("Line spacing", self._f_line))
        self._f_letter = self._mk_slider(-20, 60, 0)
        form.addWidget(Field("Letter spacing", self._f_letter))
        self._f_ink = self._mk_slider(20, 100, 100)
        form.addWidget(Field("Ink intensity", self._f_ink))
        self._f_rot = self._mk_slider(-15, 15, 0)
        form.addWidget(Field("Rotation", self._f_rot))

        vis_row = QHBoxLayout()
        vis_row.addWidget(label("Visible", "secondary"))
        vis_row.addStretch(1)
        self._f_visible = ToggleSwitch(True)
        self._f_visible.toggled.connect(self._apply_visible)
        vis_row.addWidget(self._f_visible)
        form.addLayout(vis_row)
        form.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _mk_dspin(self, suffix: str) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(0.0, 20.0)
        s.setSingleStep(0.05)
        s.setDecimals(2)
        s.setSuffix(suffix)
        return s

    def _mk_slider(self, lo: int, hi: int, val: int) -> QSlider:
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _panel_header(self, title: str, subtitle: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 12)
        lay.setSpacing(1)
        t = label(title, "subtitle")
        t.setWordWrap(False)
        lay.addWidget(t)
        lay.addWidget(label(subtitle, "muted"))
        return w

    # ----------------------------------------------------------------- bottom bar
    def _build_bottom(self) -> QWidget:
        p = theme.palette
        bar = QFrame()
        bar.setObjectName("EditorBottomBar")
        bar.setStyleSheet(f"QFrame#EditorBottomBar {{ background: {p.surface}; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(10)
        hint = label(f"{self._template.kind.value} · {self._template.dimensions_label} · "
                     f"{len(self._elements)} elements", "muted")
        lay.addWidget(hint)
        lay.addStretch(1)
        save = Button("Save", variant="secondary", icon_name="check")
        save.clicked.connect(lambda: self.ctx.toast("Document saved", "success"))
        save_as = Button("Save As…", variant="ghost")
        save_as.clicked.connect(lambda: self.ctx.toast("Saved as a copy", "success"))
        preview = Button("Preview", variant="secondary", icon_name="eye")
        preview.clicked.connect(lambda: self.ctx.toast("Opening full preview…", "info"))
        export = Button("Export", variant="primary", icon_name="share")
        export.clicked.connect(lambda: self.ctx.toast("Export started", "info"))
        for b in (save, save_as, preview, export):
            lay.addWidget(b)
        return bar

    # ------------------------------------------------------------------ behavior
    def _change_template(self, name: str) -> None:
        tpl = next((t for t in self.ctx.services.templates.list_templates()
                    if t.name == name), None)
        if not tpl:
            return
        self._template = tpl
        self._elements = copy.deepcopy(tpl.elements)
        self._canvas._w_in = tpl.width_in
        self._canvas._h_in = tpl.height_in
        self._canvas._margin_in = tpl.margin_in
        self._canvas.set_elements(self._elements)
        self._fit()
        self._show_empty_inspector()

    def _change_margin(self, value: float) -> None:
        self._canvas._margin_in = value
        self._canvas.update()

    def _on_canvas_select(self, element) -> None:
        self._selected = element
        if element is None:
            self._show_empty_inspector()
            return
        self._inspector_stack.setCurrentIndex(1)
        self._load_inspector(element)

    def _show_empty_inspector(self) -> None:
        self._inspector_stack.setCurrentIndex(0)

    def _load_inspector(self, el: TemplateElement) -> None:
        self._loading = True
        self._f_type.setText(f"{el.type.value} element · {el.name}")
        self._f_text.setPlainText(el.content)
        self._f_size.setValue(el.font_size)
        self._f_x.setValue(el.x)
        self._f_y.setValue(el.y)
        self._f_w.setValue(el.width)
        self._f_h.setValue(el.height)
        self._f_align.set_current({"left": 0, "center": 1, "right": 2}.get(el.align, 0))
        self._f_visible.setChecked(el.visible)
        self._loading = False

    def _apply_text(self) -> None:
        if self._selected and not getattr(self, "_loading", False):
            self._selected.content = self._f_text.toPlainText()
            self._canvas.update()

    def _apply_size(self, value: int) -> None:
        if self._selected and not getattr(self, "_loading", False):
            self._selected.font_size = value
            self._canvas.update()

    def _apply_pos(self) -> None:
        if self._selected and not getattr(self, "_loading", False):
            self._selected.x = self._f_x.value()
            self._selected.y = self._f_y.value()
            self._selected.width = self._f_w.value()
            self._selected.height = self._f_h.value()
            self._canvas.update()

    def _apply_align(self, index: int) -> None:
        if self._selected and not getattr(self, "_loading", False):
            self._selected.align = ["left", "center", "right"][index]
            self._canvas.update()

    def _apply_visible(self, on: bool) -> None:
        if self._selected and not getattr(self, "_loading", False):
            self._selected.visible = on
            self._canvas.update()
