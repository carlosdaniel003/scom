from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.utils.paths import resource_path


class PageHeader(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_name: str,
        chip_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        icon_badge = QFrame()
        icon_badge.setObjectName("pageHeaderIconBadge")
        icon_badge.setFixedSize(48, 48)
        icon_layout = QHBoxLayout(icon_badge)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(
            QIcon(str(resource_path("icons", icon_name))).pixmap(QSize(25, 25))
        )
        icon_layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("pageSubtitle")
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        chip = QLabel(chip_text)
        chip.setObjectName("pageChip")
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_badge, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_layout, 1)
        layout.addWidget(chip, alignment=Qt.AlignmentFlag.AlignTop)


class SectionHeader(QFrame):
    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panelSectionHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        icon_badge = QFrame()
        icon_badge.setObjectName("panelSectionIconBadge")
        icon_badge.setFixedSize(36, 36)
        icon_layout = QHBoxLayout(icon_badge)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(
            QIcon(str(resource_path("icons", icon_name))).pixmap(QSize(19, 19))
        )
        icon_layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("panelSectionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("panelSectionSubtitle")
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        self.trailing_layout = QHBoxLayout()
        self.trailing_layout.setSpacing(8)

        layout.addWidget(icon_badge)
        layout.addLayout(text_layout, 1)
        layout.addLayout(self.trailing_layout)

    def add_trailing_widget(self, widget: QWidget) -> None:
        self.trailing_layout.addWidget(widget)
