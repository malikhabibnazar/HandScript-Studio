"""A physically-accurate document preview canvas.

Draws a paper sheet at correct aspect ratio with an optional grid, print-safe
area, rulers and positioned text elements.  Elements are hit-testable so the
editors can support click-to-select.  Zooming scales everything uniformly so
proportions are always preserved.
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from models.domain import ElementType, TemplateElement
from ui.theme import theme

_SAMPLE = {
    "first_name": "Amelia", "last_name": "Hart", "sender": "The Clearwater Team",
    "street": "42 Willow Lane", "city": "Portland", "state": "OR", "zip": "97201",
    "return_street": "500 Market St", "return_city": "San Francisco, CA 94105",
}


def fill_placeholders(text: str) -> str:
    out = text
    for key, value in _SAMPLE.items():
        out = out.replace("{" + key + "}", value)
    return out


class DocumentCanvas(QWidget):
    element_selected = Signal(object)  # TemplateElement | None

    def __init__(self, width_in: float, height_in: float,
                 elements: list[TemplateElement] | None = None, *,
                 dpi: int = 96, margin_in: float = 0.2,
                 selectable: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._w_in = width_in
        self._h_in = height_in
        self._elements = elements or []
        self._dpi = dpi
        self._margin_in = margin_in
        self._zoom = 1.0
        self._pad = 56
        self._show_grid = False
        self._show_safe = True
        self._show_ruler = False
        self._selected_id: str | None = None
        self._selectable = selectable
        self._fill = True
        self.setMouseTracking(True)

    # ------------------------------------------------------------- public API
    def set_elements(self, elements: list[TemplateElement]) -> None:
        self._elements = elements
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.1, min(zoom, 4.0))
        self.updateGeometry()
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def fit(self, viewport: QSize) -> None:
        avail_w = max(100, viewport.width() - 2 * self._pad - 20)
        avail_h = max(100, viewport.height() - 2 * self._pad - 20)
        zw = avail_w / (self._w_in * self._dpi)
        zh = avail_h / (self._h_in * self._dpi)
        self.set_zoom(min(zw, zh))

    def set_grid(self, on: bool) -> None:
        self._show_grid = on
        self.update()

    def set_safe_area(self, on: bool) -> None:
        self._show_safe = on
        self.update()

    def set_ruler(self, on: bool) -> None:
        self._show_ruler = on
        self.update()

    def set_fill_placeholders(self, on: bool) -> None:
        self._fill = on
        self.update()

    def select(self, element_id: str | None) -> None:
        self._selected_id = element_id
        self.update()

    # --------------------------------------------------------------- geometry
    def _ppi(self) -> float:
        return self._dpi * self._zoom

    def _paper_size(self) -> QSize:
        return QSize(int(self._w_in * self._ppi()), int(self._h_in * self._ppi()))

    def sizeHint(self) -> QSize:  # noqa: N802
        ps = self._paper_size()
        return QSize(ps.width() + 2 * self._pad, ps.height() + 2 * self._pad)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    def _paper_rect(self) -> QRectF:
        ps = self._paper_size()
        x = (self.width() - ps.width()) / 2
        y = (self.height() - ps.height()) / 2
        return QRectF(x, y, ps.width(), ps.height())

    def _elem_rect(self, el: TemplateElement, paper: QRectF) -> QRectF:
        ppi = self._ppi()
        return QRectF(
            paper.x() + el.x * ppi,
            paper.y() + el.y * ppi,
            max(8, el.width * ppi),
            max(8, el.height * ppi),
        )

    # ---------------------------------------------------------------- painting
    def paintEvent(self, event) -> None:  # noqa: N802
        p = theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.fillRect(self.rect(), QColor(p.canvas_bg))

        paper = self._paper_rect()

        # paper (flat — distinguished by its border, not a shadow)
        painter.setBrush(QColor(p.paper))
        painter.setPen(QPen(QColor(p.paper_line), 1))
        painter.drawRect(paper)

        if self._show_grid:
            self._draw_grid(painter, paper)
        if self._show_safe:
            self._draw_safe_area(painter, paper)

        self._draw_elements(painter, paper)

        if self._show_ruler:
            self._draw_ruler(painter, paper)
        painter.end()

    def _draw_grid(self, painter: QPainter, paper: QRectF) -> None:
        pen = QPen(QColor(theme.palette.grid), 1)
        painter.setPen(pen)
        ppi = self._ppi()
        step = ppi * 0.25  # quarter-inch grid
        x = paper.x() + step
        while x < paper.right():
            painter.drawLine(int(x), int(paper.top()), int(x), int(paper.bottom()))
            x += step
        y = paper.y() + step
        while y < paper.bottom():
            painter.drawLine(int(paper.left()), int(y), int(paper.right()), int(y))
            y += step

    def _draw_safe_area(self, painter: QPainter, paper: QRectF) -> None:
        m = self._margin_in * self._ppi()
        pen = QPen(QColor(theme.palette.accent), 1, Qt.DashLine)
        pen.setDashPattern([4, 4])
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(paper.adjusted(m, m, -m, -m))

    def _draw_elements(self, painter: QPainter, paper: QRectF) -> None:
        p = theme.palette
        for el in self._elements:
            if not el.visible:
                continue
            rect = self._elem_rect(el, paper)
            selected = el.id == self._selected_id

            if el.type == ElementType.DIVIDER:
                pen = QPen(QColor(p.text), 1.4)
                painter.setPen(pen)
                mid = rect.center().y()
                painter.drawLine(int(rect.left()), int(mid), int(rect.right()), int(mid))
            elif el.type == ElementType.IMAGE:
                painter.setPen(QPen(QColor(p.border_strong), 1, Qt.DashLine))
                painter.setBrush(QColor(0, 0, 0, 8))
                painter.drawRect(rect)
                painter.setPen(QColor(p.text_muted))
                painter.drawText(rect, Qt.AlignCenter, "Image")
            else:
                text = fill_placeholders(el.content) if self._fill else el.content
                is_hand = el.type in (ElementType.TEXT, ElementType.ADDRESS)
                font = QFont(theme.type.handwriting if is_hand else theme.type.family)
                font.setPixelSize(max(6, int(el.font_size * self._zoom)))
                painter.setFont(font)
                painter.setPen(QColor(0x22, 0x22, 0x22))
                flags = Qt.TextWordWrap | Qt.AlignTop
                if el.align == "center":
                    flags |= Qt.AlignHCenter
                elif el.align == "right":
                    flags |= Qt.AlignRight
                else:
                    flags |= Qt.AlignLeft
                painter.drawText(rect, int(flags), text)

            # boundary / selection
            if selected:
                pen = QPen(QColor(p.accent), 1.5)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)
                self._draw_handles(painter, rect)
            elif self._selectable:
                painter.setPen(QPen(QColor(p.border_strong), 1, Qt.DotLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)

    def _draw_handles(self, painter: QPainter, rect: QRectF) -> None:
        painter.setBrush(QColor(theme.palette.accent))
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        r = 3.0
        for pt in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            painter.drawRect(QRectF(pt.x() - r, pt.y() - r, 2 * r, 2 * r))

    def _draw_ruler(self, painter: QPainter, paper: QRectF) -> None:
        p = theme.palette
        ppi = self._ppi()
        painter.setPen(QPen(QColor(p.text_muted), 1))
        f = QFont(theme.type.family)
        f.setPixelSize(8)
        painter.setFont(f)
        # top ruler
        inch = 0
        x = paper.x()
        while x <= paper.right() + 1:
            painter.drawLine(int(x), int(paper.top() - 10), int(x), int(paper.top() - 4))
            painter.drawText(QRect(int(x) + 2, int(paper.top() - 20), 24, 12),
                             Qt.AlignLeft, f'{inch}"')
            inch += 1
            x += ppi
        # left ruler
        inch = 0
        y = paper.y()
        while y <= paper.bottom() + 1:
            painter.drawLine(int(paper.left() - 10), int(y), int(paper.left() - 4), int(y))
            inch += 1
            y += ppi

    # ------------------------------------------------------------- interaction
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._selectable:
            return
        paper = self._paper_rect()
        pos = event.position()
        hit = None
        for el in reversed(self._elements):
            if not el.visible:
                continue
            if self._elem_rect(el, paper).contains(pos):
                hit = el
                break
        self._selected_id = hit.id if hit else None
        self.update()
        self.element_selected.emit(hit)
