from PyQt6.QtCore import QDateTime, QLocale, QSize, Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.constants import APP_NAME, APP_SUBTITLE
from src.ui.pages.dashboard_page import DashboardPage
from src.ui.pages.inventory_page import InventoryPage
from src.ui.pages.movements_page import MovementsPage
from src.ui.pages.registration_page import RegistrationPage
from src.utils.paths import resource_path


class MainWindow(QMainWindow):
    PAGE_NAMES = ["Visão geral", "Inventário e pesquisa", "Cadastrar peça", "Movimentações"]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Inventário Técnico")
        self.resize(1480, 900)
        self.setMinimumSize(1120, 700)
        self._is_fullscreen = False

        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.exit_fullscreen)

        central = QWidget()
        central.setObjectName("applicationShell")
        self.setCentralWidget(central)
        shell_layout = QHBoxLayout(central)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        content = self._build_content()

        shell_layout.addWidget(sidebar)
        shell_layout.addWidget(content, 1)

        self.registration_page.part_saved.connect(self.refresh_all)
        self.inventory_page.inventory_changed.connect(self.refresh_all)
        self.dashboard_page.inventory_imported.connect(self.reload_after_import)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        self.navigate(0)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(272)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(22, 24, 22, 22)
        sidebar_layout.setSpacing(10)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)

        brand_icon = QLabel()
        brand_icon.setObjectName("brandIcon")
        brand_icon.setFixedSize(44, 44)
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setPixmap(self._icon("circuit.svg").pixmap(QSize(27, 27)))

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        logo = QLabel(APP_NAME)
        logo.setObjectName("brandTitle")
        product_label = QLabel("INVENTÁRIO TÉCNICO")
        product_label.setObjectName("brandKicker")
        brand_text.addWidget(logo)
        brand_text.addWidget(product_label)

        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)
        sidebar_layout.addLayout(brand_row)

        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setWordWrap(True)
        subtitle.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(22)

        menu_label = QLabel("NAVEGAÇÃO")
        menu_label.setObjectName("sidebarSectionLabel")
        sidebar_layout.addWidget(menu_label)

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage()
        self.inventory_page = InventoryPage()
        self.registration_page = RegistrationPage()
        self.movements_page = MovementsPage()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.inventory_page)
        self.stack.addWidget(self.registration_page)
        self.stack.addWidget(self.movements_page)

        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("Visão geral", "dashboard.svg", 0),
            ("Inventário e pesquisa", "inventory.svg", 1),
            ("Cadastrar peça", "add-box.svg", 2),
            ("Movimentações", "history.svg", 3),
        ]
        for label, icon_name, index in nav_items:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setIcon(self._icon(icon_name))
            button.setIconSize(QSize(20, 20))
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda checked, page=index: self.navigate(page))
            self.nav_buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        environment = QFrame()
        environment.setObjectName("environmentCard")
        environment_layout = QVBoxLayout(environment)
        environment_layout.setContentsMargins(14, 12, 14, 12)
        environment_layout.setSpacing(4)

        status_row = QHBoxLayout()
        status_dot = QLabel("●")
        status_dot.setObjectName("statusDot")
        status_text = QLabel("Sistema local ativo")
        status_text.setObjectName("environmentTitle")
        status_row.addWidget(status_dot)
        status_row.addWidget(status_text)
        status_row.addStretch()

        version = QLabel("SQLite local  •  versão 0.2")
        version.setObjectName("sidebarFooter")
        environment_layout.addLayout(status_row)
        environment_layout.addWidget(version)
        sidebar_layout.addWidget(environment)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(74)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(30, 0, 30, 0)
        topbar_layout.setSpacing(14)

        breadcrumb_wrap = QVBoxLayout()
        breadcrumb_wrap.setSpacing(1)
        section_label = QLabel("SCOM  /  ÁREA TÉCNICA")
        section_label.setObjectName("topbarKicker")
        self.current_page_label = QLabel("Visão geral")
        self.current_page_label.setObjectName("topbarPageTitle")
        breadcrumb_wrap.addWidget(section_label)
        breadcrumb_wrap.addWidget(self.current_page_label)
        topbar_layout.addLayout(breadcrumb_wrap)
        topbar_layout.addStretch()

        toggle_label = QLabel("Data e hora")
        toggle_label.setObjectName("toggleLabel")
        topbar_layout.addWidget(toggle_label)

        self.clock_toggle = QCheckBox()
        self.clock_toggle.setObjectName("toggleSwitch")
        self.clock_toggle.setChecked(True)
        self.clock_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clock_toggle.setToolTip("Mostrar ou ocultar data e hora")
        self.clock_toggle.toggled.connect(self._toggle_clock)
        topbar_layout.addWidget(self.clock_toggle)

        self.datetime_panel = QFrame()
        self.datetime_panel.setObjectName("dateTimePanel")
        datetime_layout = QHBoxLayout(self.datetime_panel)
        datetime_layout.setContentsMargins(12, 7, 14, 7)
        datetime_layout.setSpacing(10)

        clock_icon = QLabel()
        clock_icon.setObjectName("dateTimeIcon")
        clock_icon.setPixmap(self._icon("clock.svg").pixmap(QSize(19, 19)))
        datetime_text = QVBoxLayout()
        datetime_text.setSpacing(0)
        self.time_label = QLabel()
        self.time_label.setObjectName("timeLabel")
        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        datetime_text.addWidget(self.time_label)
        datetime_text.addWidget(self.date_label)

        datetime_layout.addWidget(clock_icon)
        datetime_layout.addLayout(datetime_text)
        topbar_layout.addWidget(self.datetime_panel)

        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setObjectName("iconButton")
        self.fullscreen_button.setIcon(self._icon("maximize.svg"))
        self.fullscreen_button.setIconSize(QSize(20, 20))
        self.fullscreen_button.setFixedSize(40, 40)
        self.fullscreen_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_button.setToolTip("Tela cheia (F11)")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        topbar_layout.addWidget(self.fullscreen_button)

        content_layout.addWidget(topbar)
        content_layout.addWidget(self.stack, 1)
        return content

    @staticmethod
    def _icon(name: str) -> QIcon:
        return QIcon(str(resource_path("icons", name)))

    def _update_clock(self) -> None:
        now = QDateTime.currentDateTime()
        locale = QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
        self.time_label.setText(now.toString("HH:mm:ss"))
        date_text = locale.toString(now.date(), "ddd, dd MMM yyyy")
        self.date_label.setText(date_text.capitalize())

    def _toggle_clock(self, visible: bool) -> None:
        self.datetime_panel.setVisible(visible)

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.current_page_label.setText(self.PAGE_NAMES[index])
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()
        if index == 1:
            self.inventory_page.focus_search()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self._is_fullscreen = False
            self.fullscreen_button.setIcon(self._icon("maximize.svg"))
            self.fullscreen_button.setToolTip("Tela cheia (F11)")
        else:
            self.showFullScreen()
            self._is_fullscreen = True
            self.fullscreen_button.setIcon(self._icon("minimize.svg"))
            self.fullscreen_button.setToolTip("Sair da tela cheia (Esc)")

    def exit_fullscreen(self) -> None:
        if self.isFullScreen():
            self.toggle_fullscreen()

    def refresh_all(self) -> None:
        self.dashboard_page.refresh()
        self.inventory_page.refresh()
        self.movements_page.refresh()

    def reload_after_import(self) -> None:
        self.inventory_page.current_page = 1
        self.movements_page.current_page = 1
        self.registration_page.form.load_categories()
        self.registration_page.form.clear()
        self.registration_page.form.refresh_suggestions()
        self.refresh_all()
