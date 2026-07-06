import sys

from PyQt6.QtWidgets import QApplication

from src.database.schema import initialize_database
from src.ui.main_window import MainWindow
from src.utils.paths import resource_path


def load_stylesheet() -> str:
    theme_path = resource_path("styles", "theme.qss")
    return theme_path.read_text(encoding="utf-8")


def main() -> int:
    initialize_database()

    app = QApplication(sys.argv)
    app.setApplicationName("SCOM")
    app.setOrganizationName("Área Técnica")
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
