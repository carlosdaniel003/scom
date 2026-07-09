import sqlite3
from pathlib import Path

from PyQt6.QtCore import QSize, QStringListModel, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QCompleter,
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
from src.ui.widgets.page_header import PageHeader, SectionHeader
from src.utils.paths import resource_path


class PartForm(QWidget):
    UNIT_OPTIONS = {
        "Resistor": (
            ("mΩ - Miliohm", "mΩ"),
            ("Ω - Ohm", "Ω"),
            ("kΩ - Quilo-ohm", "kΩ"),
            ("MΩ - Megaohm", "MΩ"),
        ),
        "Capacitor": (
            ("pF - Picofarad", "pF"),
            ("nF - Nanofarad", "nF"),
            ("µF - Microfarad", "µF"),
            ("mF - Milifarad", "mF"),
            ("F - Farad", "F"),
        ),
        "Relé": (
            ("mV - Milivolt", "mV"),
            ("V - Volt", "V"),
        ),
        "Fusível": (
            ("mA - Miliampere", "mA"),
            ("A - Ampere", "A"),
        ),
    }

    def __init__(self, show_initial_quantity: bool = True) -> None:
        super().__init__()
        self.show_initial_quantity = show_initial_quantity
        self.selected_image_path: str | None = None
        self.categories: list[dict] = []

        root = QGridLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setHorizontalSpacing(18)
        root.setVerticalSpacing(18)

        self.image_frame = QFrame()
        self.image_frame.setObjectName("imagePanel")
        self.image_frame.setMinimumWidth(280)
        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(0, 0, 0, 18)
        image_layout.setSpacing(12)

        image_header = SectionHeader(
            "Foto da peça",
            "Identificação visual do item cadastrado.",
            "camera.svg",
        )
        image_layout.addWidget(image_header)

        image_content = QVBoxLayout()
        image_content.setContentsMargins(18, 4, 18, 0)
        image_content.setSpacing(10)

        self.image_preview = QLabel("Nenhuma imagem selecionada")
        self.image_preview.setObjectName("imagePreview")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumSize(240, 220)

        image_hint = QLabel("Formatos aceitos: PNG, JPG, WEBP e BMP")
        image_hint.setObjectName("fieldHint")
        image_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image_actions = QHBoxLayout()
        image_actions.setSpacing(8)
        select_image_button = QPushButton("Selecionar foto")
        select_image_button.setObjectName("imageActionButton")
        select_image_button.setIcon(QIcon(str(resource_path("icons", "camera.svg"))))
        select_image_button.setIconSize(QSize(17, 17))
        select_image_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_image_button.clicked.connect(self.select_image)

        clear_image_button = QPushButton("Remover")
        clear_image_button.setObjectName("secondaryButton")
        clear_image_button.setIcon(QIcon(str(resource_path("icons", "trash.svg"))))
        clear_image_button.setIconSize(QSize(16, 16))
        clear_image_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_image_button.clicked.connect(self.clear_image)

        image_actions.addWidget(select_image_button, 1)
        image_actions.addWidget(clear_image_button)

        image_content.addWidget(self.image_preview)
        image_content.addWidget(image_hint)
        image_content.addLayout(image_actions)
        image_content.addStretch()
        image_layout.addLayout(image_content)

        form_frame = QFrame()
        form_frame.setObjectName("formPanel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(0, 0, 0, 20)
        form_layout.setSpacing(0)

        form_header = SectionHeader(
            "Dados da peça",
            "Campos marcados com asterisco são obrigatórios.",
            "component.svg",
        )
        form_layout.addWidget(form_header)

        form_container = QWidget()
        form = QFormLayout(form_container)
        form.setContentsMargins(22, 16, 22, 0)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(13)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.internal_code_edit = QLineEdit()
        self.internal_code_edit.setPlaceholderText("Ex.: SMT-RES-0001")
        self.internal_code_edit.addAction(
            QIcon(str(resource_path("icons", "tag.svg"))),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nome utilizado pela área técnica")
        self.name_edit.addAction(
            QIcon(str(resource_path("icons", "component.svg"))),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Descrição técnica da peça")
        self.description_edit.setFixedHeight(76)

        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.category_changed)

        self.component_value_edit = QLineEdit()
        self.component_value_edit.setPlaceholderText("Ex.: 100")
        self.component_value_edit.setToolTip("Informe somente o valor do componente")
        self.component_value_label = self._field_label("Especificação técnica")

        self.component_unit_combo = QComboBox()
        self.component_unit_combo.setPlaceholderText("Selecione a unidade")
        self.component_unit_combo.setToolTip(
            "Selecione a unidade de medida correspondente à categoria"
        )
        self.component_unit_combo.setMinimumWidth(235)

        self.unit_column = QWidget()
        unit_layout = QVBoxLayout(self.unit_column)
        unit_layout.setContentsMargins(0, 0, 0, 0)
        unit_layout.setSpacing(5)
        unit_caption = QLabel("Unidade de medida")
        unit_caption.setObjectName("fieldHint")
        unit_layout.addWidget(unit_caption)
        unit_layout.addWidget(self.component_unit_combo)

        value_column = QWidget()
        value_layout = QVBoxLayout(value_column)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(5)
        value_caption = QLabel("Valor")
        value_caption.setObjectName("fieldHint")
        value_layout.addWidget(value_caption)
        value_layout.addWidget(self.component_value_edit)

        component_row = QWidget()
        component_layout = QHBoxLayout(component_row)
        component_layout.setContentsMargins(0, 0, 0, 0)
        component_layout.setSpacing(10)
        component_layout.addWidget(self.unit_column)
        component_layout.addWidget(value_column, 1)
        self.component_row = component_row

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_combo.setDuplicatesEnabled(False)
        self.model_combo.lineEdit().setPlaceholderText(
            "Digite ou selecione um modelo já cadastrado"
        )
        self.model_completion_model = QStringListModel(self)
        self.model_completer = QCompleter(
            self.model_completion_model,
            self.model_combo.lineEdit(),
        )
        self._configure_completer(self.model_completer)
        self.model_combo.lineEdit().setCompleter(self.model_completer)
        self.model_combo.lineEdit().textEdited.connect(self._show_model_completions)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)
        self.quantity_spin.setSuffix(" un.")
        self.quantity_control = self._build_quantity_control(self.quantity_spin)

        self.minimum_spin = QSpinBox()
        self.minimum_spin.setRange(0, 1_000_000)
        self.minimum_spin.setValue(1)
        self.minimum_spin.setSuffix(" un.")
        self.minimum_control = self._build_quantity_control(self.minimum_spin)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Ex.: Armário A / Gaveta 03")
        self.location_edit.addAction(
            QIcon(str(resource_path("icons", "location.svg"))),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.location_completion_model = QStringListModel(self)
        self.location_completer = QCompleter(
            self.location_completion_model,
            self.location_edit,
        )
        self._configure_completer(self.location_completer)
        self.location_edit.setCompleter(self.location_completer)
        self.location_edit.textEdited.connect(self._show_location_completions)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Observações adicionais, opcional")
        self.notes_edit.setFixedHeight(84)

        form.addRow(self._form_section("Identificação", "tag.svg"))
        form.addRow(self._field_label("Código interno *"), self.internal_code_edit)
        form.addRow(self._field_label("Nome da peça *"), self.name_edit)
        form.addRow(self._field_label("Descrição"), self.description_edit)

        form.addRow(self._form_section("Classificação técnica", "component.svg"))
        form.addRow(self._field_label("Categoria *"), self.category_combo)
        form.addRow(self.component_value_label, self.component_row)
        form.addRow(self._field_label("Modelo"), self.model_combo)

        form.addRow(self._form_section("Estoque e localização", "layers.svg"))
        if show_initial_quantity:
            form.addRow(self._field_label("Quantidade física"), self.quantity_control)
        form.addRow(self._field_label("Quantidade mínima"), self.minimum_control)
        form.addRow(self._field_label("Localização física *"), self.location_edit)

        form.addRow(self._form_section("Informações complementares", "notes.svg"))
        form.addRow(self._field_label("Observação"), self.notes_edit)

        form_layout.addWidget(form_container)

        root.addWidget(self.image_frame, 0, 0)
        root.addWidget(form_frame, 0, 1)
        root.setColumnStretch(1, 1)
        root.setColumnMinimumWidth(0, 280)

        self.load_categories()
        self.refresh_suggestions()

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    @staticmethod
    def _form_section(title: str, icon_name: str) -> QWidget:
        section = QWidget()
        section.setObjectName("formSection")
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 10, 0, 5)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setPixmap(
            QIcon(str(resource_path("icons", icon_name))).pixmap(QSize(16, 16))
        )
        title_label = QLabel(title.upper())
        title_label.setObjectName("formSectionTitle")
        line = QFrame()
        line.setObjectName("formSectionLine")
        line.setFrameShape(QFrame.Shape.HLine)

        layout.addWidget(icon)
        layout.addWidget(title_label)
        layout.addWidget(line, 1)
        return section

    @staticmethod
    def _build_quantity_control(spinbox: QSpinBox) -> QWidget:
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.setKeyboardTracking(False)
        spinbox.setAccelerated(True)

        minus_button = QPushButton("−")
        minus_button.setObjectName("secondaryButton")
        minus_button.setFixedWidth(42)
        minus_button.setAutoRepeat(True)
        minus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        minus_button.setToolTip("Diminuir quantidade")
        minus_button.clicked.connect(lambda checked=False: spinbox.stepDown())

        plus_button = QPushButton("+")
        plus_button.setObjectName("secondaryButton")
        plus_button.setFixedWidth(42)
        plus_button.setAutoRepeat(True)
        plus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_button.setToolTip("Aumentar quantidade")
        plus_button.clicked.connect(lambda checked=False: spinbox.stepUp())

        control = QWidget()
        control_layout = QHBoxLayout(control)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)
        control_layout.addWidget(minus_button)
        control_layout.addWidget(spinbox, 1)
        control_layout.addWidget(plus_button)
        return control

    @staticmethod
    def _configure_completer(completer: QCompleter) -> None:
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setMaxVisibleItems(10)

    def _show_model_completions(self, text: str) -> None:
        if text.strip() and self.model_completion_model.rowCount() > 0:
            self.model_completer.setCompletionPrefix(text)
            self.model_completer.complete()

    def _show_location_completions(self, text: str) -> None:
        if text.strip() and self.location_completion_model.rowCount() > 0:
            self.location_completer.setCompletionPrefix(text)
            self.location_completer.complete()

    def refresh_suggestions(self) -> None:
        self.location_completion_model.setStringList(PartRepository.list_locations())

        index = self.category_combo.currentIndex()
        if 0 <= index < len(self.categories):
            current_model = self.model_combo.currentText()
            category_id = int(self.categories[index]["id"])
            self._load_model_options(category_id, current_model)

    def _load_model_options(self, category_id: int, current_text: str = "") -> None:
        models = PartRepository.list_models(category_id)
        self.model_completion_model.setStringList(models)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setCurrentText(current_text)

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
        category_name = category["name"]
        required = bool(category["requires_component_value"])
        label_text = category["value_label"] or "Especificação técnica"
        unit_options = self.UNIT_OPTIONS.get(category_name, ())

        self.component_value_label.setText(f"{label_text}{' *' if required else ''}")
        self.component_value_label.setVisible(required)
        self.component_row.setVisible(required)

        self.component_unit_combo.clear()
        for display_name, unit_code in unit_options:
            self.component_unit_combo.addItem(display_name, unit_code)
        self.unit_column.setVisible(bool(unit_options))

        default_unit = category["default_unit"] or ""
        default_index = self.component_unit_combo.findData(default_unit)
        if default_index >= 0:
            self.component_unit_combo.setCurrentIndex(default_index)
        elif unit_options:
            self.component_unit_combo.setCurrentIndex(0)

        current_model = self.model_combo.currentText()
        self._load_model_options(int(category["id"]), current_model)

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
                232,
                210,
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
        component_unit = self.component_unit_combo.currentData() or ""

        if not internal_code:
            raise ValueError("Informe o código interno.")
        if not name:
            raise ValueError("Informe o nome da peça.")
        if not location:
            raise ValueError("Informe a localização física.")
        if category["requires_component_value"] and not component_value:
            raise ValueError(f"Informe: {category['value_label']}.")
        if self.UNIT_OPTIONS.get(category["name"]) and not component_unit:
            raise ValueError("Selecione a unidade de medida.")

        return PartInput(
            internal_code=internal_code,
            name=name,
            description=self.description_edit.toPlainText().strip(),
            category_id=int(category["id"]),
            component_value=component_value,
            component_unit=str(component_unit),
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
        self.category_changed()
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

        stored_unit = part.get("component_unit") or ""
        if stored_unit:
            unit_index = self.component_unit_combo.findData(stored_unit)
            if unit_index < 0:
                self.component_unit_combo.addItem(
                    f"{stored_unit} - Unidade cadastrada",
                    stored_unit,
                )
                unit_index = self.component_unit_combo.findData(stored_unit)
            self.component_unit_combo.setCurrentIndex(unit_index)

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
        root.setContentsMargins(30, 26, 30, 30)
        root.setSpacing(18)

        header = PageHeader(
            "Cadastrar peça",
            "Registre componentes, materiais e ferramentas da área técnica.",
            "add-box.svg",
            "NOVO REGISTRO",
        )
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 7, 0)
        container_layout.setSpacing(14)

        self.form = PartForm(show_initial_quantity=True)
        container_layout.addWidget(self.form)

        action_bar = QFrame()
        action_bar.setObjectName("actionBar")
        actions = QHBoxLayout(action_bar)
        actions.setContentsMargins(16, 12, 16, 12)
        actions.setSpacing(10)

        required_hint = QLabel("* Preenchimento obrigatório")
        required_hint.setObjectName("requiredHint")
        actions.addWidget(required_hint)
        actions.addStretch()

        clear_button = QPushButton("Limpar formulário")
        clear_button.setObjectName("secondaryButton")
        clear_button.setIcon(QIcon(str(resource_path("icons", "clear.svg"))))
        clear_button.setIconSize(QSize(17, 17))
        clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_button.clicked.connect(self.form.clear)

        save_button = QPushButton("Cadastrar peça")
        save_button.setObjectName("primaryButton")
        save_button.setIcon(QIcon(str(resource_path("icons", "save.svg"))))
        save_button.setIconSize(QSize(17, 17))
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.clicked.connect(self.save)

        actions.addWidget(clear_button)
        actions.addWidget(save_button)
        container_layout.addWidget(action_bar)
        container_layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

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
        self.form.refresh_suggestions()
        self.part_saved.emit()
