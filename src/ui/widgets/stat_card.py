from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", object_name: str = "statCard") -> None:
        super().__init__()
        self.setObjectName(object_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(6)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        title_label = QLabel(title)
        title_label.setObjectName("statTitle")

        layout.addWidget(self.value_label)
        layout.addWidget(title_label)

    def set_value(self, value: int | str) -> None:
        self.value_label.setText(str(value))
