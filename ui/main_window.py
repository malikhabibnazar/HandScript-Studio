"""The application shell: sidebar, top bar, page stack and navigation."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext
from ui.components import IconButton, ToastHost, label
from ui.layouts.sidebar import Sidebar
from ui.pages.batch_generator import BatchGeneratorPage
from ui.pages.batch_progress import BatchProgressPage
from ui.pages.dashboard import DashboardPage
from ui.pages.document_editor import DocumentEditorPage
from ui.pages.documents import DocumentsPage
from ui.pages.exports import ExportsPage
from ui.pages.handwriting_detail import HandwritingDetailPage
from ui.pages.handwriting_profiles import HandwritingProfilesPage
from ui.pages.onboarding import OnboardingPage
from ui.pages.settings import SettingsPage
from ui.pages.template_editor import TemplateEditorPage
from ui.pages.templates import TemplatesPage
from ui.theme import apply_theme, icons, theme

# which sidebar section a (possibly detail) page belongs to
SECTION_OF = {
    "dashboard": "dashboard",
    "documents": "documents",
    "document_editor": "documents",
    "templates": "templates",
    "template_editor": "templates",
    "handwriting": "handwriting",
    "handwriting_detail": "handwriting",
    "batch": "batch",
    "batch_progress": "batch",
    "exports": "exports",
    "settings": "settings",
}

SINGLETON_PAGES = {
    "dashboard": DashboardPage,
    "documents": DocumentsPage,
    "templates": TemplatesPage,
    "handwriting": HandwritingProfilesPage,
    "batch": BatchGeneratorPage,
    "exports": ExportsPage,
    "settings": SettingsPage,
}

DYNAMIC_PAGES = {
    "document_editor": DocumentEditorPage,
    "template_editor": TemplateEditorPage,
    "handwriting_detail": HandwritingDetailPage,
    "batch_progress": BatchProgressPage,
}


class MainWindow(QWidget):
    def __init__(self, services) -> None:
        super().__init__()
        self.setObjectName("AppRoot")
        self.setWindowTitle("HandScript Studio")
        self.resize(1360, 880)
        self.setMinimumSize(1040, 680)

        self.ctx = AppContext(
            services=services,
            navigate=self.navigate,
            toast=self.show_toast,
            set_theme=self.set_theme,
            current_theme=lambda: theme.mode,
        )

        self._singletons: dict[str, QWidget] = {}
        self._dynamic_widget: QWidget | None = None
        self._current_key = "onboarding"

        # root stack switches between onboarding (full screen) and the shell
        self._root = QStackedWidget(self)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self._root)

        self._shell = self._build_shell()
        self._onboarding = OnboardingPage(self.ctx)
        self._root.addWidget(self._onboarding)
        self._root.addWidget(self._shell)

        self.toasts = ToastHost(self)

        self._install_shortcuts()
        self._root.setCurrentWidget(self._onboarding)

    # ------------------------------------------------------------------ shell
    def _build_shell(self) -> QWidget:
        shell = QWidget()
        lay = QHBoxLayout(shell)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.navigate)
        lay.addWidget(self.sidebar)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        right_lay.addWidget(self.stack, stretch=1)
        lay.addWidget(right, stretch=1)
        return shell

    def _build_topbar(self) -> QWidget:
        p = theme.palette
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"QFrame#TopBar {{ background: {p.window}; border-bottom: 1px solid {p.border}; }}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 18, 0)
        lay.setSpacing(10)

        self._collapse_btn = IconButton("sidebar", tooltip="Toggle sidebar  (⌘/Ctrl+B)", size=34)
        self._collapse_btn.clicked.connect(self._toggle_sidebar)
        lay.addWidget(self._collapse_btn)

        self._crumb = label("Dashboard", "secondary")
        self._crumb.setWordWrap(False)
        self._crumb.setStyleSheet("font-weight: 600;")
        lay.addWidget(self._crumb)
        lay.addStretch(1)

        self._theme_btn = IconButton("sun" if theme.is_dark else "moon",
                                     tooltip="Toggle appearance", size=34)
        self._theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self._theme_btn)

        help_btn = IconButton("help", tooltip="Help & keyboard shortcuts", size=34)
        help_btn.clicked.connect(lambda: self.show_toast(
            "Shortcuts: ⌘1–6 navigate · ⌘B sidebar · ⌘N new document", "info"))
        lay.addWidget(help_btn)
        return bar

    def _install_shortcuts(self) -> None:
        mapping = {
            "Ctrl+1": "dashboard", "Ctrl+2": "documents", "Ctrl+3": "templates",
            "Ctrl+4": "handwriting", "Ctrl+5": "batch", "Ctrl+6": "exports",
            "Ctrl+,": "settings",
        }
        for seq, key in mapping.items():
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(lambda k=key: self.navigate(k))
        sc_b = QShortcut(QKeySequence("Ctrl+B"), self)
        sc_b.activated.connect(self._toggle_sidebar)
        sc_n = QShortcut(QKeySequence("Ctrl+N"), self)
        sc_n.activated.connect(lambda: self.navigate("document_editor", document_id=None))

    # ------------------------------------------------------------- navigation
    def navigate(self, key: str, **params) -> None:
        if key == "onboarding":
            self._root.setCurrentWidget(self._onboarding)
            return

        # leaving onboarding -> show the shell
        if self._root.currentWidget() is self._onboarding:
            self._root.setCurrentWidget(self._shell)

        self._current_key = key
        if key in DYNAMIC_PAGES:
            page = DYNAMIC_PAGES[key](self.ctx, **params)
            if self._dynamic_widget is not None:
                self.stack.removeWidget(self._dynamic_widget)
                self._dynamic_widget.deleteLater()
            self._dynamic_widget = page
            self.stack.addWidget(page)
            self.stack.setCurrentWidget(page)
        else:
            if key not in self._singletons:
                self._singletons[key] = SINGLETON_PAGES[key](self.ctx)
                self.stack.addWidget(self._singletons[key])
            page = self._singletons[key]
            # let singletons refresh their data when revisited
            if hasattr(page, "on_show"):
                page.on_show()
            self.stack.setCurrentWidget(page)

        section = SECTION_OF.get(key, key)
        self.sidebar.set_active(section)
        self._crumb.setText(self._title_for(key, params))

    def _title_for(self, key: str, params: dict) -> str:
        titles = {
            "dashboard": "Dashboard", "documents": "Documents", "templates": "Templates",
            "handwriting": "Handwriting", "batch": "Batch Generator", "exports": "Exports",
            "settings": "Settings", "document_editor": "Documents / Editor",
            "template_editor": "Templates / Editor", "handwriting_detail": "Handwriting / Profile",
            "batch_progress": "Batch Generator / Progress",
        }
        return titles.get(key, key.title())

    # ------------------------------------------------------------------ chrome
    def _toggle_sidebar(self) -> None:
        self.sidebar.set_collapsed(not self.sidebar.is_collapsed())

    def _toggle_theme(self) -> None:
        self.set_theme("light" if theme.is_dark else "dark")

    def set_theme(self, mode: str) -> None:
        if mode == theme.mode:
            return
        app = QApplication.instance()
        apply_theme(app, mode)
        self._rebuild_after_theme()

    def _rebuild_after_theme(self) -> None:
        """Rebuild palette-dependent widgets so inline styles pick up new colors."""
        current = self._current_key
        in_onboarding = self._root.currentWidget() is self._onboarding

        # drop cached pages so they rebuild with the new palette
        for w in self._singletons.values():
            self.stack.removeWidget(w)
            w.deleteLater()
        self._singletons.clear()
        if self._dynamic_widget is not None:
            self.stack.removeWidget(self._dynamic_widget)
            self._dynamic_widget.deleteLater()
            self._dynamic_widget = None

        # rebuild shell chrome (sidebar + top bar use inline palette styles)
        old_shell = self._shell
        self._shell = self._build_shell()
        self._root.insertWidget(1, self._shell)
        self._root.removeWidget(old_shell)
        old_shell.deleteLater()

        if in_onboarding:
            old_onb = self._onboarding
            self._onboarding = OnboardingPage(self.ctx)
            self._root.insertWidget(0, self._onboarding)
            self._root.removeWidget(old_onb)
            old_onb.deleteLater()
            self._root.setCurrentWidget(self._onboarding)
        else:
            self.navigate(current)

    def show_toast(self, message: str, tone: str = "info") -> None:
        self.toasts.show_toast(message, tone)
