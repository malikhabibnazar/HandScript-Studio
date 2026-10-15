"""Batch Generation Progress — live processing view and completion screen.

The progress here is driven by a QTimer purely to animate the mock.  In the real
application the batch engine will run on a QThread / QThreadPool and emit
progress signals; this view is already shaped around that (it only consumes
``update(generated, failed, current_item)`` style updates), so swapping the mock
driver for real worker signals won't change the UI.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext
from ui.components import (
    Breadcrumb,
    Button,
    Card,
    IconButton,
    SectionHeader,
    confirm,
    hline,
    label,
)
from ui.theme import icons, theme


class ProgressRing(QWidget):
    def __init__(self, size: int = 150, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._size = size
        self.setFixedSize(size, size)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        margin = 10
        rect = QRectF(margin, margin, self._size - 2 * margin, self._size - 2 * margin)
        painter.setPen(QPen(QColor(p.neutral_soft), 10))
        painter.drawArc(rect, 0, 360 * 16)
        pen = QPen(QColor(p.accent), 10)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -int(360 * 16 * self._value))
        painter.setPen(QColor(p.text))
        f = QFont(theme.type.family)
        f.setPixelSize(30)
        f.setWeight(QFont.Bold)
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignCenter, f"{int(self._value * 100)}%")
        painter.end()


class BatchProgressPage(QWidget):
    def __init__(self, ctx: AppContext, *, config: dict | None = None,
                 batch_id: str | None = None) -> None:
        super().__init__()
        self.ctx = ctx
        if config is None and batch_id:
            batch = ctx.services.batches.get_batch(batch_id)
            config = {"name": batch.name, "total": batch.total,
                      "output_dir": batch.output_dir, "format": batch.export_format.value}
        config = config or {"name": "New Batch", "total": 250,
                            "output_dir": "~/HandScript/Exports/new-batch", "format": "PDF"}
        self._cfg = config
        self._total = int(config.get("total", 250))
        self._generated = 0
        self._failed = 0
        self._cancelled = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())
        root.addWidget(hline())

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_progress_view())
        self._stack.addWidget(QWidget())  # completion placeholder, built on finish
        root.addWidget(self._stack, stretch=1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(110)

    # ------------------------------------------------------------------- chrome
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(32, 16, 24, 14)
        col = QVBoxLayout()
        col.setSpacing(4)
        crumb = Breadcrumb(["Batch Generator", "Progress"])
        crumb.navigate.connect(lambda i: self.ctx.navigate("batch"))
        col.addWidget(crumb)
        t = label(self._cfg["name"], "title")
        t.setWordWrap(False)
        col.addWidget(t)
        lay.addLayout(col)
        lay.addStretch(1)
        return bar

    def _wrap(self, inner: QWidget) -> QWidget:
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(32, 24, 32, 28)
        lay.addStretch(1)
        col = QWidget()
        col.setMaximumWidth(920)
        cl = QVBoxLayout(col)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(18)
        cl.addWidget(inner)
        lay.addWidget(col, stretch=1000)
        lay.addStretch(1)
        return wrap

    # ------------------------------------------------------------- progress view
    def _build_progress_view(self) -> QWidget:
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(32, 24, 32, 28)
        outer.setSpacing(18)
        inner = QWidget()
        inner.setMaximumWidth(920)
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(18)

        top = Card(padding=24, spacing=0)
        row = QHBoxLayout()
        row.setSpacing(28)
        self._ring = ProgressRing(148)
        row.addWidget(self._ring)

        stats = QVBoxLayout()
        stats.setSpacing(10)
        self._status_label = label("Generating documents…", "subtitle")
        self._status_label.setWordWrap(False)
        stats.addWidget(self._status_label)
        self._eta_label = label("Estimating time remaining…", "muted")
        stats.addWidget(self._eta_label)
        stats.addSpacing(4)

        chips = QHBoxLayout()
        chips.setSpacing(10)
        self._c_generated = self._stat("Generated", "0", "success")
        self._c_remaining = self._stat("Remaining", str(self._total), "neutral")
        self._c_failed = self._stat("Failed", "0", "warning")
        chips.addWidget(self._c_generated)
        chips.addWidget(self._c_remaining)
        chips.addWidget(self._c_failed)
        chips.addStretch(1)
        stats.addLayout(chips)
        stats.addSpacing(6)
        self._current_label = label("Current item: —", "secondary")
        self._current_label.setWordWrap(False)
        stats.addWidget(self._current_label)
        row.addLayout(stats, stretch=1)
        top.add_layout(row)
        col.addWidget(top)

        actions = QHBoxLayout()
        self._cancel_btn = Button("Cancel", variant="dangerGhost", icon_name="stop")
        self._cancel_btn.clicked.connect(self._cancel)
        errors_btn = Button("View errors", variant="ghost", icon_name="warning")
        errors_btn.clicked.connect(lambda: self.ctx.toast(
            f"{self._failed} failed item(s) logged", "warning"))
        actions.addWidget(self._cancel_btn)
        actions.addWidget(errors_btn)
        actions.addStretch(1)
        col.addLayout(actions)

        self._log_card = Card(padding=18, spacing=2)
        self._log_card.add(SectionHeader("Activity log"))
        self._log_card.add(hline())
        self._log_layout = self._log_card.layout()
        col.addWidget(self._log_card)
        col.addStretch(1)

        outer.addWidget(inner, alignment=Qt.AlignHCenter)
        return container

    def _stat(self, name: str, value: str, tone: str) -> QFrame:
        p = theme.palette
        fg = {"success": p.success, "warning": p.warning, "neutral": p.text}.get(tone, p.text)
        f = QFrame()
        f.setStyleSheet(f"background: {p.surface_alt}; border: 1px solid {p.border};"
                        " border-radius: 2px;")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 9, 22, 9)
        lay.setSpacing(0)
        v = label(value, "subtitle")
        v.setObjectName("statval")
        v.setStyleSheet(f"color: {fg}; font-weight: 700;")
        v.setWordWrap(False)
        lay.addWidget(v)
        lay.addWidget(label(name, "caption"))
        f._value_label = v  # type: ignore
        return f

    def _log(self, kind: str, text: str) -> None:
        p = theme.palette
        icon_name, tone = {
            "ok": ("check-circle", p.success), "skip": ("info", p.text_muted),
            "export": ("share", p.accent), "error": ("warning", p.danger),
        }.get(kind, ("dot", p.text_muted))
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 7, 0, 7)
        lay.setSpacing(10)
        ic = label("")
        ic.setPixmap(icons.pixmap(icon_name, tone, 15))
        ic.setFixedSize(15, 15)
        lay.addWidget(ic)
        lay.addWidget(label(text, "secondary"), stretch=1)
        self._log_layout.addWidget(row)
        # keep log from growing unbounded
        if self._log_layout.count() > 22:
            item = self._log_layout.takeAt(2)
            if item and item.widget():
                item.widget().deleteLater()

    # -------------------------------------------------------------- simulation
    def _tick(self) -> None:
        if self._cancelled:
            return
        step = max(1, self._total // 60)
        self._generated += step
        if self._generated % (step * 7) < step and self._generated < self._total:
            self._failed += 1
            self._log("error", f"Error rendering document_{self._generated:04d}.{self._ext()}")
        if self._generated >= self._total:
            self._generated = self._total - self._failed
            self._finish()
            return
        self._refresh_progress()
        if self._generated % (step * 4) < step:
            self._log("ok", f"Generated document_{self._generated:04d}.{self._ext()}")

    def _ext(self) -> str:
        return "png" if self._cfg.get("format") == "PNG" else "pdf"

    def _refresh_progress(self) -> None:
        done = self._generated + self._failed
        self._ring.set_value(done / self._total if self._total else 0)
        self._c_generated._value_label.setText(f"{self._generated:,}")  # type: ignore
        self._c_remaining._value_label.setText(  # type: ignore
            f"{max(0, self._total - done):,}")
        self._c_failed._value_label.setText(str(self._failed))  # type: ignore
        self._current_label.setText(
            f"Current item: document_{min(done + 1, self._total):04d}.{self._ext()}")
        remaining_ticks = max(0, (self._total - done)) / max(1, self._total // 60)
        secs = int(remaining_ticks * 0.11)
        self._eta_label.setText(f"About {secs}s remaining" if secs else "Finishing up…")

    def _cancel(self) -> None:
        if confirm(self, "Cancel generation?",
                   "The batch will stop. Files already generated are kept.",
                   confirm_text="Stop batch", destructive=True):
            self._cancelled = True
            self._timer.stop()
            self.ctx.toast("Batch cancelled", "warning")
            self.ctx.navigate("batch")

    def _finish(self) -> None:
        self._timer.stop()
        self._log("export", "Export completed")
        completion = self._build_completion()
        self._stack.removeWidget(self._stack.widget(1))
        self._stack.insertWidget(1, completion)
        self._stack.setCurrentIndex(1)
        self.ctx.toast("Generation complete", "success")

    # ------------------------------------------------------------- completion
    def _build_completion(self) -> QWidget:
        p = theme.palette
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(32, 40, 32, 32)
        outer.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        card = Card(padding=34, spacing=16)
        card.setMaximumWidth(560)
        card.layout().setAlignment(Qt.AlignHCenter)

        badge = QFrame()
        badge.setFixedSize(66, 66)
        badge.setStyleSheet(f"background: {p.success_soft}; border-radius: 2px;")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = label("")
        ic.setPixmap(icons.pixmap("check-circle", p.success, 34))
        ic.setAlignment(Qt.AlignCenter)
        bl.addWidget(ic)
        card.add(badge)
        card.layout().setAlignment(badge, Qt.AlignHCenter)

        title = label("Generation Complete", "title")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(False)
        card.add(title)
        sub = label(f"Your batch “{self._cfg['name']}” finished processing.", "secondary")
        sub.setAlignment(Qt.AlignCenter)
        card.add(sub)

        card.add(hline())
        totals = QHBoxLayout()
        totals.setSpacing(12)
        totals.addWidget(self._stat("Total", f"{self._total:,}", "neutral"))
        totals.addWidget(self._stat("Successful", f"{self._generated:,}", "success"))
        totals.addWidget(self._stat("Failed", str(self._failed), "warning"))
        totals_wrap = QWidget()
        totals_wrap.setLayout(totals)
        card.add(totals_wrap)

        out_row = QFrame()
        out_row.setStyleSheet(f"background: {p.surface_alt}; border: 1px solid {p.border};"
                              " border-radius: 2px;")
        orl = QHBoxLayout(out_row)
        orl.setContentsMargins(14, 10, 14, 10)
        orl.setSpacing(8)
        fic = label("")
        fic.setPixmap(icons.pixmap("folder", p.text_secondary, 16))
        orl.addWidget(fic)
        orl.addWidget(label(self._cfg["output_dir"], "secondary"))
        orl.addStretch(1)
        card.add(out_row)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        again = Button("Generate Again", variant="ghost", icon_name="refresh")
        again.clicked.connect(lambda: self.ctx.navigate("batch"))
        results = Button("View Results", variant="secondary", icon_name="documents")
        results.clicked.connect(lambda: self.ctx.navigate("exports"))
        open_folder = Button("Open Output Folder", variant="primary", icon_name="folder-open")
        open_folder.clicked.connect(lambda: self.ctx.toast("Opening output folder…", "info"))
        actions.addWidget(again)
        actions.addWidget(results)
        actions.addWidget(open_folder)
        actions_wrap = QWidget()
        actions_wrap.setLayout(actions)
        card.add(actions_wrap)

        outer.addWidget(card, alignment=Qt.AlignHCenter)
        return container
