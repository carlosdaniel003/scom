import sqlite3
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.part import PartInput
from src.repositories.category_repository import CategoryRepository
from src.repositories.part_repository import PartRepository
from src.services.image_service import store_part_image


class PartForm(QWidget):
    def __init__(self, show_initial_quantity: bool = True) -> None:
        super().__init__()
        self.show_initial_quantity = show_initial_quantity
        self.selected_image_path: str | None = None
        self.categories: list[dict] = []

        root = QGridLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setHorizontalSpacing(24)
        root.setVerticalSpacing(18)

        self.image_frame = QFrame()
        self.image_frame.setObjectName("imagePanel")
        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(18, 18, 18, 18)
        image_layout.setSpacing(12)

        self.image_preview = QLabel("Nenhuma imagem selecionada")
        self.image_preview.setObjectName("imagePreview")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumSize(230, 210)

        select_image_button = QPushButton("Selecionar foto")
        select_image_button.clicked.connect(self.select_image)
        clear_image_button = QPushButton("Remover foto")
        clear_image_button.setObjectName("secondaryButton")
        clear_image_button.clicked.connect(self.clear_image)

        image_layout.addWidget(self.image_preview)
        image_layout.addWidget(select_image_button)
        image_layout.addWidget(clear_image_button)
        image_layout.addStretch()

        form_frame = QFrame()
        form_frame.setObjectName("formPanel")
        form = QFormLayout(form_frame)
        form.setContentsMargins(24, 24, 24, 24)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(15)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.internal_code_edit = QLineEdit()
        self.internal_code_edit.setPlaceholderText("Ex.: SMT-RES-0001")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nome utilizado pela área técnica")

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Descrição técnica da peça")
        self.description_edit.setFixedHeight(80)

        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.category_changed)

        self.component_value_edit = QLineEdit()
        self.component_value_edit.setPlaceholderText("Informe o valor técnico")
        self.component_value_label = QLabel("Valor do componente")

        self.component_unit_edit = QLineEdit()
        self.component_unit_edit.setPlaceholderText("Unidade")
        self.component_unit_edit.setMaximumWidth(130)

        component_row = QWidget()
        component_layout = QHBoxLayout(component_row)
        component_layout.setContentsMargins(0, 0, 0, 0)
        component_layout.setSpacing(10)
        component_layout.addWidget(self.component_value_edit)
        component_layout.addWidget(self.component_unit_edit)
        self.component_row = component_row

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.lineEdit().setPlaceholderText("Digite ou selecione um modelo já cadastrado")

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)

        self.minimum_spin = QSpinBox()
        self.minimum_spin.setRange(0, 1_000_000)
        self.minimum_spin.setValue(1)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Ex.: Armário A / Gaveta 03")

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Observações adicionais, opcional")
        self.notes_edit.setFixedHeight(90)

        form.addRow("Código interno *", self.internal_code_edit)
        form.addRow("Nome da peça *", self.name_edit)
        form.addRow("Descrição", self.description_edit)
        form.addRow("Categoria *", self.category_combo)
        form.addRow(self.component_value_label, self.component_row)
        form.addRow("Modelo", self.model_combo)
        if show_initial_quantity:
            form.addRow("Quantidade física", self.quantity_spin)
        form.addRow("Quantidade mínima", self.minimum_spin)
        form.addRow("Localização física *", self.location_edit)
        form.addRow("Observação", self.notes_edit)

        root.addWidget(self.image_frame, 0, 0)
        root.addWidget(form_frame, 0, 1)
        root.setColumnStretch(1, 1)

        self.load_categories()

    def load_categories(self) -> None:
        self.categories = CategoryRepository.list_all()
        self.category_combo.clear()
        for category in self.categories:
            self.category_combo.addItem(category["name"], category["id"])
        self.category_changed()

    def category_changed(self) -> None:
        index = self.category_combo.currentIndex()
        if index < 0 or index >= len(self.categories):
            return
        category = self.categories[index]
        required = bool(category["requires_component_value"])
        label_text = category["value_label"] or "Valor do componente"
        self.component_value_label.setText(f"{label_text}{' *' if required else ''}")
        self.component_value_label.setVisible(required)
        self.component_row.setVisible(required)
        self.component_unit_edit.setText(category["default_unit"] or "")

        current_text = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(PartRepository.list_models(int(category["id"])))
        self.model_combo.setCurrentText(current_text)

    def select_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar foto da peça",
            "",
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.selected_image_path = path
            self.show_image(path)

    def show_image(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.image_preview.setText("Não foi possível abrir a imagem")
            return
        self.image_preview.setPixmap(
            pixmap.scaled(
                220,
                200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def clear_image(self) -> None:
        self.selected_image_path = None
        self.image_preview.clear()
        self.image_preview.setText("Nenhuma imagem selecionada")

    def collect_data(self) -> PartInput:
        category_index = self.category_combo.currentIndex()
        if category_index < 0:
            raise ValueError("Selecione uma categoria.")
        category = self.categories[category_index]

        internal_code = self.internal_code_edit.text().strip()
        name = self.name_edit.text().strip()
        location = self.location_edit.text().strip()
        component_value = self.component_value_edit.text().strip()

        if not internal_code:
            raise ValueError("Informe o código interno.")
        if not name:
            raise ValueError("Informe o nome da peça.")
        if not location:
            raise ValueError("Informe a localização física.")
        if category["requires_component_value"] and not component_value:
            raise ValueError(f"Informe: {category['value_label']}.")

        return PartInput(
            internal_code=internal_code,
            name=name,
            description=self.description_edit.toPlainText().strip(),
            category_id=int(category["id"]),
            component_value=component_value,
            component_unit=self.component_unit_edit.text().strip(),
            model_name=self.model_combo.currentText().strip(),
            current_quantity=self.quantity_spin.value() if self.show_initial_quantity else 0,
            minimum_quantity=self.minimum_spin.value(),
            physical_location=location,
            notes=self.notes_edit.toPlainText().strip(),
            image_path=self.selected_image_path,
        )

    def clear(self) -> None:
        self.internal_code_edit.clear()
        self.name_edit.clear()
        self.description_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.component_value_edit.clear()
        self.model_combo.setCurrentText("")
        self.quantity_spin.setValue(0)
        self.minimum_spin.setValue(1)
        self.location_edit.clear()
        self.notes_edit.clear()
        self.clear_image()
        self.internal_code_edit.setFocus()

    def load_part(self, part: dict) -> None:
        self.internal_code_edit.setText(part.get("internal_code") or "")
        self.name_edit.setText(part.get("name") or "")
        self.description_edit.setPlainText(part.get("description") or "")
        category_id = int(part["category_id"])
        category_index = self.category_combo.findData(category_id)
        if category_index >= 0:
            self.category_combo.setCurrentIndex(category_index)
        self.component_value_edit.setText(part.get("component_value") or "")
        self.component_unit_edit.setText(part.get("component_unit") or "")
        self.model_combo.setCurrentText(part.get("model_name") or "")
        self.minimum_spin.setValue(int(part.get("minimum_quantity") or 0))
        self.location_edit.setText(part.get("physical_location") or "")
        self.notes_edit.setPlainText(part.get("notes") or "")
        image_path = part.get("image_path")
        if image_path and Path(image_path).exists():
            self.selected_image_path = image_path
            self.show_image(image_path)


class RegistrationPage(QWidget):
    part_saved = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 32)
        root.setSpacing(20)

        title = QLabel("Cadastro de peças")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Cadastre componentes, materiais e ferramentas da área técnica.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 6, 0)
        container_layout.setSpacing(18)

        self.form = PartForm(show_initial_quantity=True)
        container_layout.addWidget(self.form)

        actions = QHBoxLayout()
        actions.addStretch()
        clear_button = QPushButton("Limpar formulário")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(self.form.clear)
        save_button = QPushButton("Cadastrar peça")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save)
        actions.addWidget(clear_button)
        actions.addWidget(save_button)
        container_layout.addLayout(actions)
        container_layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def save(self) -> None:
        try:
            data = self.form.collect_data()
            stored_image = store_part_image(data.image_path)
            data.image_path = stored_image
            PartRepository.create(data)
        except (ValueError, sqlite3.IntegrityError) as error:
            message = str(error)
            if "UNIQUE constraint failed: parts.internal_code" in message:
                message = "Já existe uma peça cadastrada com esse código interno."
            QMessageBox.warning(self, "Não foi possível cadastrar", message)
            return

        QMessageBox.information(self, "Peça cadastrada", "A peça foi cadastrada com sucesso.")
        self.form.clear()
        self.part_saved.emit()
