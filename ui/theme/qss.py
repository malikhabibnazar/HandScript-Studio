"""Builds the global Qt Style Sheet from the active palette.

Widgets opt into variants through Qt *dynamic properties* (set via
``widget.setProperty(...)``) rather than bespoke subclassing, e.g.::

    btn.setProperty("variant", "primary")
    label.setProperty("role", "title")

The design is intentionally flat and square: a single small corner radius
(``R``) is used everywhere, with light borders — no large rounded cards and no
shadows — so surfaces read as crisp, technical panels.
"""
from __future__ import annotations

from .tokens import Palette, Typography

# One small corner radius for the whole UI.
R = 2


def build_qss(p: Palette, t: Typography) -> str:
    s = t.sizes
    fam = t.family
    return f"""
/* ====================  BASE  ==================== */
* {{
    font-family: "{fam}";
    font-size: {s.body}px;
    color: {p.text};
    outline: 0;
}}
QWidget {{
    background: transparent;
    color: {p.text};
}}
QMainWindow, QDialog {{
    background: {p.window};
}}
/* The top-level app window is a plain QWidget; paint its backdrop so uncovered
   regions never fall back to the platform default (black on Windows). */
QWidget#AppRoot {{
    background: {p.window};
}}
QToolTip {{
    background: {p.text};
    color: {p.window};
    border: none;
    border-radius: {R}px;
    padding: 6px 9px;
    font-size: {s.small}px;
}}

/* ====================  TEXT ROLES  ==================== */
QLabel[role="display"]  {{ font-size: {s.display}px;  font-weight: 700; color: {p.text}; }}
QLabel[role="title"]    {{ font-size: {s.title}px;    font-weight: 700; color: {p.text}; }}
QLabel[role="titleSm"]  {{ font-size: {s.title_sm}px; font-weight: 600; color: {p.text}; }}
QLabel[role="subtitle"] {{ font-size: {s.subtitle}px; font-weight: 600; color: {p.text}; }}
QLabel[role="section"]  {{ font-size: {s.small}px;    font-weight: 700; color: {p.text_muted};
                           letter-spacing: 1px; text-transform: uppercase; }}
QLabel[role="body"]     {{ font-size: {s.body}px;     color: {p.text}; }}
QLabel[role="secondary"]{{ font-size: {s.body}px;     color: {p.text_secondary}; }}
QLabel[role="muted"]    {{ font-size: {s.small}px;    color: {p.text_muted}; }}
QLabel[role="caption"]  {{ font-size: {s.caption}px;  color: {p.text_muted}; }}
QLabel[role="accent"]   {{ color: {p.accent_text}; font-weight: 600; }}
QLabel[role="danger"]   {{ color: {p.danger}; }}
QLabel[role="metric"]   {{ font-size: {s.title_lg}px; font-weight: 700; color: {p.text}; }}
QLabel:disabled {{ color: {p.text_muted}; }}

/* ====================  CARDS / PANELS  ==================== */
QFrame#Card {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {R}px;
}}
QFrame#CardAlt {{
    background: {p.surface_alt};
    border: 1px solid {p.border};
    border-radius: {R}px;
}}
QFrame#Inset {{
    background: {p.surface_alt};
    border: 1px solid {p.divider};
    border-radius: {R}px;
}}
QFrame[role="hline"] {{ background: {p.divider}; max-height: 1px; min-height: 1px; border: none; }}
QFrame[role="vline"] {{ background: {p.divider}; max-width: 1px; min-width: 1px; border: none; }}

/* ====================  BUTTONS  ==================== */
QPushButton {{
    background: {p.control};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: {R}px;
    padding: 7px 14px;
    font-size: {s.body}px;
    font-weight: 600;
    min-height: 18px;
}}
QPushButton:hover {{ background: {p.control_hover}; border-color: {p.border_strong}; }}
QPushButton:pressed {{ background: {p.control_pressed}; }}
QPushButton:disabled {{ color: {p.text_muted}; background: {p.control}; border-color: {p.border}; }}

QPushButton[variant="primary"] {{
    background: {p.accent};
    color: {p.text_on_accent};
    border: 1px solid {p.accent};
}}
QPushButton[variant="primary"]:hover {{ background: {p.accent_hover}; border-color: {p.accent_hover}; }}
QPushButton[variant="primary"]:pressed {{ background: {p.accent_pressed}; border-color: {p.accent_pressed}; }}
QPushButton[variant="primary"]:disabled {{ background: {p.accent_soft}; color: {p.text_on_accent};
                                           border-color: {p.accent_soft}; }}

QPushButton[variant="soft"] {{
    background: {p.accent_soft};
    color: {p.accent_text};
    border: 1px solid transparent;
}}
QPushButton[variant="soft"]:hover {{ border-color: {p.accent}; }}

QPushButton[variant="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {p.text_secondary};
}}
QPushButton[variant="ghost"]:hover {{ background: {p.control_hover}; color: {p.text}; }}

QPushButton[variant="danger"] {{
    background: {p.danger};
    color: #FFFFFF;
    border: 1px solid {p.danger};
}}
QPushButton[variant="danger"]:hover {{ background: #B32424; border-color: #B32424; }}

QPushButton[variant="dangerGhost"] {{
    background: transparent;
    color: {p.danger};
    border: 1px solid {p.border};
}}
QPushButton[variant="dangerGhost"]:hover {{ background: {p.danger_soft}; border-color: {p.danger}; }}

QPushButton[size="lg"] {{ padding: 10px 20px; font-size: {s.body_lg}px; }}
QPushButton[size="sm"] {{ padding: 4px 10px; font-size: {s.small}px; }}

/* Icon-only tool buttons */
QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {R}px;
    padding: 6px;
}}
QToolButton:hover {{ background: {p.control_hover}; }}
QToolButton:pressed {{ background: {p.control_pressed}; }}
QToolButton:checked {{ background: {p.accent_soft}; }}
QToolButton[variant="accent"]:checked {{ background: {p.accent_soft}; }}

/* ====================  INPUTS  ==================== */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {p.control};
    border: 1px solid {p.border};
    border-radius: {R}px;
    padding: 7px 10px;
    color: {p.text};
    selection-background-color: {p.accent_soft};
    selection-color: {p.text};
}}
QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {p.border_strong}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {p.accent}; padding: 6px 9px; }}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
    background: {p.surface_alt}; color: {p.text_muted}; }}
QLineEdit[role="search"] {{ padding-left: 32px; }}
QLineEdit::placeholder {{ color: {p.text_muted}; }}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{ width: 16px; border: none; background: transparent; }}

/* ====================  COMBOBOX  ==================== */
QComboBox {{
    background: {p.control};
    border: 1px solid {p.border};
    border-radius: {R}px;
    padding: 7px 10px;
    min-height: 18px;
    color: {p.text};
}}
QComboBox:hover {{ border-color: {p.border_strong}; }}
QComboBox:focus {{ border: 2px solid {p.accent}; padding: 6px 9px; }}
QComboBox::drop-down {{ width: 26px; border: none; subcontrol-position: right center; }}
QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
QComboBox QAbstractItemView {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {R}px;
    padding: 4px;
    selection-background-color: {p.accent_soft};
    selection-color: {p.accent_text};
    outline: 0;
}}
QComboBox QAbstractItemView::item {{ padding: 7px 10px; border-radius: {R}px; min-height: 20px; }}

/* ====================  CHECK / RADIO  ==================== */
QCheckBox, QRadioButton {{ spacing: 8px; color: {p.text}; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 18px; height: 18px; }}
QCheckBox::indicator {{ border: 1px solid {p.border_strong}; border-radius: {R}px; background: {p.control}; }}
QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
QCheckBox::indicator:checked {{ background: {p.accent}; border-color: {p.accent};
    image: url(:/check); }}
QRadioButton::indicator {{ border: 1px solid {p.border_strong}; border-radius: {R}px; background: {p.control}; }}
QRadioButton::indicator:checked {{ border: 5px solid {p.accent}; background: {p.control}; }}

/* ====================  TABS  ==================== */
QTabWidget::pane {{ border: none; top: -1px; }}
QTabBar {{ qproperty-drawBase: 0; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {p.text_secondary};
    padding: 8px 14px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: {p.text}; }}
QTabBar::tab:selected {{ color: {p.accent_text}; border-bottom: 2px solid {p.accent}; }}

/* ====================  TABLES / LISTS  ==================== */
QTableView, QTreeView, QListView {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {R}px;
    gridline-color: transparent;
    selection-background-color: {p.accent_soft};
    selection-color: {p.text};
    alternate-background-color: {p.surface_alt};
    outline: 0;
}}
QTableView::item, QTreeView::item, QListView::item {{
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {p.divider};
    color: {p.text};
}}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
    background: {p.accent_soft}; color: {p.text};
}}
QHeaderView {{ background: {p.surface_alt}; }}
QHeaderView::section {{
    background: {p.surface_alt};
    color: {p.text_muted};
    padding: 9px 10px;
    border: none;
    border-bottom: 1px solid {p.border};
    font-size: {s.small}px;
    font-weight: 700;
    text-align: left;
}}
QHeaderView::section:first {{ border-top-left-radius: {R}px; }}
QHeaderView::section:last {{ border-top-right-radius: {R}px; }}
QTableCornerButton::section {{ background: {p.surface_alt}; border: none; }}

/* ====================  SCROLLBARS  ==================== */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.scrollbar}; border-radius: {R}px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: {p.scrollbar_hover}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p.scrollbar}; border-radius: {R}px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover {{ background: {p.scrollbar_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; background: none; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ====================  PROGRESS  ==================== */
QProgressBar {{
    background: {p.neutral_soft};
    border: none;
    border-radius: {R}px;
    height: 8px;
    text-align: center;
    color: {p.text_secondary};
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: {R}px; }}

/* ====================  SLIDER  ==================== */
QSlider::groove:horizontal {{ height: 4px; background: {p.neutral_soft}; border-radius: {R}px; }}
QSlider::sub-page:horizontal {{ background: {p.accent}; border-radius: {R}px; }}
QSlider::handle:horizontal {{
    background: {p.surface}; border: 1px solid {p.border_strong};
    width: 14px; height: 14px; margin: -6px 0; border-radius: {R}px;
}}
QSlider::handle:horizontal:hover {{ border-color: {p.accent}; }}

/* ====================  MENU  ==================== */
QMenu {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {R}px;
    padding: 5px;
}}
QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: {R}px; color: {p.text}; }}
QMenu::item:selected {{ background: {p.accent_soft}; color: {p.accent_text}; }}
QMenu::separator {{ height: 1px; background: {p.divider}; margin: 5px 8px; }}

/* ====================  GROUPBOX  ==================== */
QGroupBox {{
    border: 1px solid {p.border};
    border-radius: {R}px;
    margin-top: 14px;
    padding: 14px;
    background: {p.surface};
    font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {p.text_secondary}; }}

/* ====================  SPLITTER  ==================== */
QSplitter::handle {{ background: {p.divider}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QSplitter::handle:hover {{ background: {p.border_strong}; }}
"""
