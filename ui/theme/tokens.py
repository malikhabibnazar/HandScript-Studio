"""Design tokens for HandScript Studio.

A single source of truth for colors, spacing, radii, typography and elevation.
Two palettes are provided (light / dark). The rest of the UI reads from the
active :class:`Theme` singleton so the whole application restyles atomically.

Nothing in here imports Qt widgets — tokens are plain data so they can be used
by the QSS builder, by custom-painted widgets and by tests alike.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
#   Color palettes                                                            #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Palette:
    """A complete set of semantic colors for one appearance."""

    name: str

    # Surfaces (back-to-front)
    window: str          # app background
    sidebar: str         # navigation rail
    surface: str         # cards / panels
    surface_alt: str     # subtle inset / zebra rows / toolbars
    overlay: str         # modal scrim

    # Text
    text: str            # primary
    text_secondary: str  # labels, captions
    text_muted: str      # placeholders, disabled
    text_on_accent: str  # text on accent fills

    # Lines
    border: str          # default separators / control outlines
    border_strong: str   # focused / emphasised outlines
    divider: str         # hairline dividers inside surfaces

    # Accent
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str     # tinted background (selection, soft buttons)
    accent_text: str     # accent used as foreground text

    # Status (foreground + soft background pairs)
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    info: str
    info_soft: str
    neutral: str
    neutral_soft: str

    # Control fills
    control: str          # input / button neutral fill
    control_hover: str
    control_pressed: str

    # Canvas (document editor)
    canvas_bg: str        # workspace behind the "paper"
    paper: str            # the document sheet
    paper_line: str       # safe-area / guide lines
    grid: str             # grid dots / lines

    # Misc
    shadow: str           # rgba string used by QGraphicsDropShadow helpers
    scrollbar: str
    scrollbar_hover: str


LIGHT = Palette(
    name="light",
    window="#F4F5F7",
    sidebar="#ECEEF1",
    surface="#FFFFFF",
    surface_alt="#F7F8FA",
    overlay="rgba(17, 20, 24, 0.38)",
    text="#1D1D1F",
    text_secondary="#5C6066",
    text_muted="#9095A0",
    text_on_accent="#FFFFFF",
    border="#E2E4E8",
    border_strong="#C9CCD2",
    divider="#EDEEF1",
    accent="#2D6CDF",
    accent_hover="#2A62C8",
    accent_pressed="#2455AE",
    accent_soft="#E8F0FD",
    accent_text="#2259C4",
    success="#1E8E3E",
    success_soft="#E6F4EA",
    warning="#B26A00",
    warning_soft="#FBEEDC",
    danger="#C62828",
    danger_soft="#FBE9E9",
    info="#2D6CDF",
    info_soft="#E8F0FD",
    neutral="#6B7280",
    neutral_soft="#EEF0F3",
    control="#FFFFFF",
    control_hover="#F2F3F5",
    control_pressed="#E9EBEE",
    canvas_bg="#DCDFE4",
    paper="#FFFFFF",
    paper_line="#C7CBD4",
    grid="#E3E6EB",
    shadow="rgba(17, 20, 24, 0.14)",
    scrollbar="#C7CBD2",
    scrollbar_hover="#AEB3BC",
)


DARK = Palette(
    name="dark",
    window="#1B1D21",
    sidebar="#17181B",
    surface="#23262B",
    surface_alt="#2A2D33",
    overlay="rgba(0, 0, 0, 0.55)",
    text="#F2F3F5",
    text_secondary="#AFB4BD",
    text_muted="#71767F",
    text_on_accent="#FFFFFF",
    border="#34383F",
    border_strong="#474C55",
    divider="#2E3238",
    accent="#4C8DFF",
    accent_hover="#5F99FF",
    accent_pressed="#3C7BEA",
    accent_soft="#223049",
    accent_text="#8CB6FF",
    success="#5CC77A",
    success_soft="#1E3326",
    warning="#E7A33E",
    warning_soft="#392E1A",
    danger="#F0726B",
    danger_soft="#3A2322",
    info="#4C8DFF",
    info_soft="#223049",
    neutral="#9AA0A9",
    neutral_soft="#2C3036",
    control="#2A2D33",
    control_hover="#31353C",
    control_pressed="#373C44",
    canvas_bg="#121316",
    paper="#F7F7F5",
    paper_line="#B9BDC6",
    grid="#2B2F35",
    shadow="rgba(0, 0, 0, 0.5)",
    scrollbar="#3A3F47",
    scrollbar_hover="#4C525B",
)


# --------------------------------------------------------------------------- #
#   Scale tokens (appearance independent)                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Spacing:
    xxs: int = 2
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 20
    xxl: int = 24
    xxxl: int = 32
    section: int = 40


@dataclass(frozen=True)
class Radius:
    # Flat, square design language: one small corner radius everywhere.
    xs: int = 2
    sm: int = 2
    md: int = 2
    lg: int = 2
    xl: int = 2
    pill: int = 2


@dataclass(frozen=True)
class FontSizes:
    caption: int = 11
    small: int = 12
    body: int = 13
    body_lg: int = 14
    subtitle: int = 15
    title_sm: int = 17
    title: int = 20
    title_lg: int = 24
    display: int = 28


@dataclass
class Typography:
    # Resolved at runtime in app.py depending on the platform.
    family: str = "Segoe UI"
    mono: str = "Cascadia Code"
    handwriting: str = "Segoe Script"
    sizes: FontSizes = field(default_factory=FontSizes)


SPACING = Spacing()
RADIUS = Radius()


# --------------------------------------------------------------------------- #
#   Active theme                                                              #
# --------------------------------------------------------------------------- #
class Theme:
    """Holds the active palette + scale tokens.

    Treated as a lightweight singleton via the module-level ``theme`` instance.
    """

    def __init__(self) -> None:
        self.palette: Palette = LIGHT
        self.spacing: Spacing = SPACING
        self.radius: Radius = RADIUS
        self.type: Typography = Typography()

    # -- appearance -------------------------------------------------------- #
    def set_mode(self, mode: str) -> None:
        self.palette = DARK if mode == "dark" else LIGHT

    @property
    def mode(self) -> str:
        return self.palette.name

    @property
    def is_dark(self) -> bool:
        return self.palette.name == "dark"

    # -- convenience ------------------------------------------------------- #
    def color(self, key: str) -> str:
        return getattr(self.palette, key)


theme = Theme()
