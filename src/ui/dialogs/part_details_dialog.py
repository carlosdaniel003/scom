from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QVBoxLayout


class PartDetailsDialog(QDialog):
    def __init__(self, part: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detalhes da peça")
        self.setMinimumSize(620, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 26, 26, 26)
        root.setSpacing(18)

        title = QLabel(f"{part['internal_code']} — {part['name']}")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        image = QLabel("Sem imagem")
        image.setObjectName("imagePreview")
        image.setFixedHeight(150)
        image.setScaledContents(False)
        if part.get("image_path"):
            pixmap = QPixmap(part["image_path"])
            if not pixmap.isNull():
                image.setPixmap(
                    pixmap.scaled(
                        240,
                        140,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        root.addWidget(image)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

        component = "—"
        if part.get("component_value"):
            component = f"{part['component_value']} {part.get('component_unit') or ''}".strip()

        fields = [
            ("Categoria", part.get("category_name") or "—"),
            ("Modelo", part.get("model_name") or "—"),
            ("Valor técnico", component),
            ("Quantidade", str(part.get("current_quantity", 0))),
            ("Quantidade mínima", str(part.get("minimum_quantity", 0))),
            ("Localização", part.get("physical_location") or "—"),
            ("Status", part.get("stock_status") or "—"),
            ("Cadastro", part.get("created_at") or "—"),
            ("Última atualização", part.get("updated_at") or "—"),
            ("Descrição", part.get("description") or "—"),
            ("Observação", part.get("notes") or "—"),
        ]

        for row, (label, value) in enumerate(fields):
            key = QLabel(label)
            key.setObjectName("detailKey")
            content = QLabel(value)
            content.setWordWrap(True)
            content.setObjectName("detailValue")
            grid.addWidget(key, row, 0)
            grid.addWidget(content, row, 1)

        root.addLayout(grid)
        root.addStretch()

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
