"""Small shared building blocks: labels, lines, cards, chips, avatars."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.theme import card_shadow, icons, theme


# --------------------------------------------------------------------------- #
#   Labels                                                                    #
# --------------------------------------------------------------------------- #
def label(text: str = "", role: str = "body", parent: QWidget | None = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setProperty("role", role)
    if role in ("secondary", "muted", "body", "caption"):
        lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def repolish(w: QWidget) -> None:
    """Re-evaluate the stylesheet for a widget after changing a dynamic property."""
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


# --------------------------------------------------------------------------- #
#   Dividers                                                                  #
# --------------------------------------------------------------------------- #
def hline(parent: QWidget | None = None) -> QFrame:
    f = QFrame(parent)
    f.setProperty("role", "hline")
    f.setFixedHeight(1)
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return f


def vline(parent: QWidget | None = None) -> QFrame:
    f = QFrame(parent)
    f.setProperty("role", "vline")
    f.setFixedWidth(1)
    f.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    return f


def spacer(h: int = 0) -> QWidget:
    w = QWidget()
    if h:
        w.setFixedHeight(h)
    else:
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return w


# --------------------------------------------------------------------------- #
#   Card                                                                      #
# --------------------------------------------------------------------------- #
class Card(QFrame):
    """An elevated surface with comfortable padding."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        padding: int = 20,
        spacing: int = 14,
        shadow: bool = False,
        alt: bool = False,
        object_name: str = "Card",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CardAlt" if alt else object_name)
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(padding, padding, padding, padding)
        self._v.setSpacing(spacing)
        if shadow:
            self.setGraphicsEffect(card_shadow())

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._v

    def add(self, w: QWidget) -> QWidget:
        self._v.addWidget(w)
        return w

    def add_layout(self, lay) -> None:
        self._v.addLayout(lay)

    def add_stretch(self, stretch: int = 1) -> None:
        self._v.addStretch(stretch)


# --------------------------------------------------------------------------- #
#   Icon + text row                                                           #
# --------------------------------------------------------------------------- #
class IconText(QWidget):
    def __init__(self, icon_name: str, text: str, *, role: str = "body",
                 color: str | None = None, size: int = 16, gap: int = 8,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(gap)
        self._icon = QLabel()
        self._color = color or theme.palette.text_secondary
        self._size = size
        self._name = icon_name
        self._icon.setPixmap(icons.pixmap(icon_name, self._color, size))
        self._icon.setFixedSize(size, size)
        lay.addWidget(self._icon)
        self._label = label(text, role)
        self._label.setWordWrap(False)
        lay.addWidget(self._label)
        lay.addStretch(1)

    def set_text(self, text: str) -> None:
        self._label.setText(text)


# --------------------------------------------------------------------------- #
#   Avatar / monogram                                                         #
# --------------------------------------------------------------------------- #
class Avatar(QWidget):
    """A circular monogram derived from a name — used for handwriting profiles."""

    _PALETTE = ["#2D6CDF", "#1E8E3E", "#B26A00", "#7A49C9", "#C62828", "#0C8599"]

    def __init__(self, name: str, size: int = 40, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self.setFixedSize(size, size)
        self._size = size

    def _initials(self) -> str:
        parts = [p for p in self._name.replace("—", " ").split() if p[:1].isalnum()]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[1][0]).upper()

    def _bg(self) -> QColor:
        idx = sum(ord(c) for c in self._name) % len(self._PALETTE)
        return QColor(self._PALETTE[idx])

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self._size, self._size, 2, 2)
        bg = self._bg()
        bg.setAlpha(42)
        p.fillPath(path, bg)
        pen_color = self._bg()
        f = QFont(theme.type.family)
        f.setPixelSize(int(self._size * 0.38))
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(pen_color)
        p.drawText(self.rect(), Qt.AlignCenter, self._initials())
        p.end()
