from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Inventário Técnico")
        self.resize(1450, 860)
        self.setMinimumSize(1120, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 22)
        sidebar_layout.setSpacing(10)

        logo = QLabel(APP_NAME)
        logo.setObjectName("brandTitle")
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setWordWrap(True)
        subtitle.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(28)

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
            ("Visão geral", 0),
            ("Inventário e pesquisa", 1),
            ("Cadastrar peça", 2),
            ("Movimentações", 3),
        ]
        for label, index in nav_items:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda checked, page=index: self.navigate(page))
            self.nav_buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()
        version = QLabel("Banco local SQLite\nVersão inicial 0.1")
        version.setObjectName("sidebarFooter")
        sidebar_layout.addWidget(version)

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)

        self.registration_page.part_saved.connect(self.refresh_all)
        self.inventory_page.inventory_changed.connect(self.refresh_all)

        self.navigate(0)

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()
        if index == 1:
            self.inventory_page.focus_search()

    def refresh_all(self) -> None:
        self.dashboard_page.refresh()
        self.inventory_page.refresh()
        self.movements_page.refresh()
