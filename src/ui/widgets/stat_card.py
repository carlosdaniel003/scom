from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.utils.paths import resource_path


class StatCard(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "0",
        object_name: str = "statCard",
        icon_name: str = "package.svg",
        helper_text: str = "",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setMinimumHeight(142)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 17)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon_badge = QFrame()
        icon_badge.setObjectName("statIconBadge")
        icon_badge.setFixedSize(38, 38)
        icon_layout = QHBoxLayout(icon_badge)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(
            QIcon(str(resource_path("icons", icon_name))).pixmap(QSize(20, 20))
        )
        icon_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        header.addWidget(icon_badge)
        header.addWidget(title_label)
        header.addStretch()

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")

        helper_label = QLabel(helper_text)
        helper_label.setObjectName("statHelper")
        helper_label.setVisible(bool(helper_text))

        layout.addLayout(header)
        layout.addWidget(self.value_label)
        layout.addWidget(helper_label)

    def set_value(self, value: int | str) -> None:
        self.value_label.setText(str(value))
