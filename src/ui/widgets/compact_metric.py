from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.utils.paths import resource_path


class CompactMetric(QFrame):
    def __init__(
        self,
        title: str,
        icon_name: str,
        object_name: str = "compactMetric",
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setMinimumHeight(82)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        icon_badge = QFrame()
        icon_badge.setObjectName("compactMetricIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_layout = QHBoxLayout(icon_badge)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(
            QIcon(str(resource_path("icons", icon_name))).pixmap(QSize(21, 21))
        )
        icon_layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self.value_label = QLabel("0")
        self.value_label.setObjectName("compactMetricValue")
        title_label = QLabel(title)
        title_label.setObjectName("compactMetricTitle")
        text_layout.addWidget(self.value_label)
        text_layout.addWidget(title_label)

        layout.addWidget(icon_badge)
        layout.addLayout(text_layout, 1)

    def set_value(self, value: int | str) -> None:
        self.value_label.setText(str(value))
