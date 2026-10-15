"""Crisp, theme-aware line icons.

Icons are defined once as SVG path markup (24x24, stroke-based) and rendered to
``QPixmap`` / ``QIcon`` on demand at any color and size.  Using vector SVG keeps
them razor sharp on Retina / high-DPI screens and lets us recolor a single set
for light and dark themes.

Usage::

    from ui.theme import icons
    label.setPixmap(icons.pixmap("search", color=theme.palette.text_muted, size=16))
    btn.setIcon(icons.icon("plus", color="#FFFFFF"))
"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# 24x24 viewBox, stroke = currentColor.  Keep strokes clean and consistent.
_PATHS: dict[str, str] = {
    # ---- navigation ----
    "dashboard": '<rect x="3" y="3" width="7" height="8" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/>'
                 '<rect x="14" y="11" width="7" height="10" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>',
    "documents": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
                 '<path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/>',
    "templates": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>',
    "handwriting": '<path d="M4 20c3-1 4-9 7-9 2 0 1 5 3 5 2 0 3-4 5-4"/>'
                   '<path d="M14.5 4.5l3 3L8 17l-4 1 1-4z"/>',
    "batch": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    "exports": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
               '<path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "settings": '<path d="M4 7h10"/><path d="M18 7h2"/><path d="M4 17h4"/><path d="M12 17h8"/>'
                '<circle cx="16" cy="7" r="2.3"/><circle cx="10" cy="17" r="2.3"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.4 2.3c-.8.3-1.4 1-1.4 1.9v.3"/>'
            '<circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>',

    # ---- actions ----
    "plus": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    "filter": '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    "sort": '<path d="M7 4v16"/><path d="M4 8l3-4 3 4"/><path d="M17 20V4"/><path d="M14 16l3 4 3-4"/>',
    "more": '<circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none"/>'
            '<circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/>'
            '<circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none"/>',
    "more-v": '<circle cx="12" cy="5" r="1.4" fill="currentColor" stroke="none"/>'
              '<circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/>'
              '<circle cx="12" cy="19" r="1.4" fill="currentColor" stroke="none"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
    "close": '<path d="M6 6l12 12"/><path d="M18 6L6 18"/>',
    "check": '<path d="M5 12l5 5 9-11"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5.5"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
             '<path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/><path d="M10 11v6"/><path d="M14 11v6"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/>',
    "duplicate": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/>',
    "share": '<path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7"/><path d="M8 7l4-4 4 4"/><path d="M12 3v13"/>',
    "open": '<path d="M9 5h10a2 2 0 0 1 2 2v10"/><path d="M15 15L5 5"/><path d="M5 11v8h8"/>',
    "play": '<path d="M7 5l12 7-12 7z"/>',
    "pause": '<rect x="7" y="5" width="3.5" height="14" rx="1"/><rect x="13.5" y="5" width="3.5" height="14" rx="1"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-1 5"/><path d="M20 4v6h-6"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "folder-open": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2"/><path d="M3 9h18l-2.2 9a1 1 0 0 1-1 .8H6.2a1 1 0 0 1-1-.8z"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M4 18l5-4 4 3 3-3 4 4"/>',
    "upload": '<path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/><path d="M8 8l4-4 4 4"/><path d="M12 4v12"/>',
    "download": '<path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/><path d="M8 11l4 4 4-4"/><path d="M12 15V3"/>',
    "zoom-in": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/><path d="M11 8v6"/><path d="M8 11h6"/>',
    "zoom-out": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/><path d="M8 11h6"/>',
    "grid": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>'
            '<path d="M3 9h18"/><path d="M3 15h18"/>',
    "ruler": '<rect x="3" y="7" width="18" height="10" rx="1.5" transform="rotate(0 12 12)"/>'
             '<path d="M7 7v3"/><path d="M11 7v4"/><path d="M15 7v3"/><path d="M19 7v3" stroke-width="0"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="2.6"/>',
    "eye-off": '<path d="M4 4l16 16"/><path d="M9.5 5.4A10 10 0 0 1 12 5c6.5 0 10 7 10 7a16 16 0 0 1-3.2 3.9"/>'
               '<path d="M6.3 7.6A16 16 0 0 0 2 12s3.5 7 10 7a10 10 0 0 0 3.3-.6"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "unlock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.5-2"/>',
    "rotate": '<path d="M4 9a8 8 0 0 1 13-3l3 3"/><path d="M20 4v5h-5"/><path d="M20 15a8 8 0 0 1-13 3l-3-3"/>',
    "align-left": '<path d="M4 6h16"/><path d="M4 12h10"/><path d="M4 18h13"/>',
    "align-center": '<path d="M4 6h16"/><path d="M7 12h10"/><path d="M5 18h14"/>',
    "align-right": '<path d="M4 6h16"/><path d="M10 12h10"/><path d="M7 18h13"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none"/>',
    "warning": '<path d="M12 4l9 15H3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>',
    "error": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6"/><path d="M15 9l-6 6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M8 3v4"/><path d="M16 3v4"/>',
    "menu": '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>',
    "sidebar": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "star-fill": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" '
                 'fill="currentColor"/>',
    "grip": '<circle cx="9" cy="6" r="1.1" fill="currentColor" stroke="none"/><circle cx="15" cy="6" r="1.1" fill="currentColor" stroke="none"/>'
            '<circle cx="9" cy="12" r="1.1" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="1.1" fill="currentColor" stroke="none"/>'
            '<circle cx="9" cy="18" r="1.1" fill="currentColor" stroke="none"/><circle cx="15" cy="18" r="1.1" fill="currentColor" stroke="none"/>',
    "file-csv": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
                '<path d="M8 13h2"/><path d="M8 16h2"/><path d="M14 13h2"/><path d="M14 16h2"/>',
    "file-txt": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
                '<path d="M8 12h8"/><path d="M8 15h8"/><path d="M8 18h5"/>',
    "text": '<path d="M5 6h14"/><path d="M12 6v13"/><path d="M8 19h8"/>',
    "envelope": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M4 7l8 6 8-6"/>',
    "card": '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M7 10h7"/><path d="M7 13h10"/>',
    "add-image": '<rect x="3" y="5" width="13" height="13" rx="2"/><circle cx="8" cy="10" r="1.6"/>'
                 '<path d="M4 17l4-3 3 2"/><path d="M19 4v6"/><path d="M16 7h6"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18 2 2 0 0 0 2-2c0-1.2-1-1.5-1-2.5A1.5 1.5 0 0 1 16.5 13H18a3 3 0 0 0 3-3 7 7 0 0 0-9-7z"/>'
               '<circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7.5" r="1"/><circle cx="14.5" cy="7.5" r="1"/>',
    "sparkle": '<path d="M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6z"/>'
               '<path d="M18 15l.7 1.8L20.5 17.5l-1.8.7L18 20l-.7-1.8L15.5 17.5l1.8-.7z"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    "database": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/>'
                '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/>'
           '<path d="M9 3v3"/><path d="M15 3v3"/><path d="M9 18v3"/><path d="M15 18v3"/>'
           '<path d="M3 9h3"/><path d="M3 15h3"/><path d="M18 9h3"/><path d="M18 15h3"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
    "printer": '<path d="M6 9V4h12v5"/><rect x="4" y="9" width="16" height="7" rx="1.5"/>'
               '<path d="M7 16h10v4H7z"/><circle cx="17" cy="12" r="0.6" fill="currentColor" stroke="none"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.3 6.3 0 0 0 10.5 10.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M2 12h2"/>'
           '<path d="M20 12h2"/><path d="M5 5l1.5 1.5"/><path d="M17.5 17.5L19 19"/><path d="M19 5l-1.5 1.5"/><path d="M6.5 17.5L5 19"/>',
    "check-small": '<path d="M6 12l4 4 8-9"/>',
    "dot": '<circle cx="12" cy="12" r="4" fill="currentColor" stroke="none"/>',
}


def _svg(name: str, color: str) -> bytes:
    inner = _PATHS.get(name)
    if inner is None:
        inner = _PATHS["dot"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{inner}</svg>'
    ).encode("utf-8")


@lru_cache(maxsize=1024)
def pixmap(name: str, color: str = "#1D1D1F", size: int = 20, dpr: float = 2.0) -> QPixmap:
    """Render an icon to a QPixmap at the given color and logical size."""
    renderer = QSvgRenderer(QByteArray(_svg(name, color)))
    px = int(size * dpr)
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str = "#1D1D1F", size: int = 20) -> QIcon:
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size))
    return ic


def icon_size(size: int = 18) -> QSize:
    return QSize(size, size)
