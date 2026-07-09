from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.repositories.movement_repository import MovementRepository


class MovementDialog(QDialog):
    movement_saved = pyqtSignal()

    def __init__(self, part: dict, parent=None, forced_type: str | None = None) -> None:
        super().__init__(parent)
        self.part = part
        self.available_quantity = max(0, int(part["current_quantity"]))
        self.setWindowTitle("Movimentação de estoque")
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        title = QLabel(f"{part['internal_code']} — {part['name']}")
        title.setObjectName("dialogTitle")
        available = QLabel(f"Quantidade disponível: {self.available_quantity}")
        available.setObjectName("mutedText")
        root.addWidget(title)
        root.addWidget(available)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["ENTRADA", "SAÍDA"])
        if forced_type:
            self.type_combo.setCurrentText(forced_type)
            self.type_combo.setEnabled(False)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.quantity_spin.setRange(1, 1_000_000)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quantity_spin.setAccelerated(True)
        self.quantity_spin.setKeyboardTracking(False)
        self.quantity_spin.setMinimumWidth(160)

        self.minus_button = QPushButton("−")
        self.minus_button.setObjectName("secondaryButton")
        self.minus_button.setFixedWidth(42)
        self.minus_button.setAutoRepeat(True)
        self.minus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minus_button.setToolTip("Diminuir quantidade")
        self.minus_button.clicked.connect(lambda: self.quantity_spin.stepDown())

        self.plus_button = QPushButton("+")
        self.plus_button.setObjectName("secondaryButton")
        self.plus_button.setFixedWidth(42)
        self.plus_button.setAutoRepeat(True)
        self.plus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plus_button.setToolTip("Aumentar quantidade")
        self.plus_button.clicked.connect(lambda: self.quantity_spin.stepUp())

        quantity_widget = QWidget()
        quantity_layout = QHBoxLayout(quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(8)
        quantity_layout.addWidget(self.minus_button)
        quantity_layout.addWidget(self.quantity_spin, 1)
        quantity_layout.addWidget(self.plus_button)

        self.quantity_hint = QLabel()
        self.quantity_hint.setObjectName("mutedText")
        self.quantity_hint.setWordWrap(True)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Ex.: Reposição, manutenção, consumo em reparo")

        self.responsible_edit = QLineEdit()
        self.responsible_edit.setPlaceholderText("Nome do responsável")

        form.addRow("Tipo", self.type_combo)
        form.addRow("Quantidade", quantity_widget)
        form.addRow("", self.quantity_hint)
        form.addRow("Motivo", self.reason_edit)
        form.addRow("Responsável", self.responsible_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Registrar")
        self.save_button.setObjectName("primaryButton")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.type_combo.currentTextChanged.connect(self.update_quantity_limit)
        self.quantity_spin.valueChanged.connect(self.update_quantity_hint)
        self.update_quantity_limit()

    def update_quantity_limit(self) -> None:
        is_output = self.type_combo.currentText() == "SAÍDA"

        if is_output:
            has_stock = self.available_quantity > 0
            if has_stock:
                self.quantity_spin.setRange(1, self.available_quantity)
                if self.quantity_spin.value() < 1:
                    self.quantity_spin.setValue(1)
            else:
                self.quantity_spin.setRange(0, 0)
                self.quantity_spin.setValue(0)

            self.quantity_spin.setEnabled(has_stock)
            self.minus_button.setEnabled(has_stock)
            self.plus_button.setEnabled(has_stock)
            self.save_button.setEnabled(has_stock)
            self.quantity_spin.setToolTip(
                f"Máximo disponível para retirada: {self.available_quantity}"
            )
        else:
            self.quantity_spin.setEnabled(True)
            self.minus_button.setEnabled(True)
            self.plus_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.quantity_spin.setRange(1, 1_000_000)
            if self.quantity_spin.value() < 1:
                self.quantity_spin.setValue(1)
            self.quantity_spin.setToolTip("Informe a quantidade de entrada")

        self.update_quantity_hint()

    def update_quantity_hint(self) -> None:
        quantity = self.quantity_spin.value()
        if self.type_combo.currentText() == "SAÍDA":
            if self.available_quantity == 0:
                self.quantity_hint.setText("Sem estoque disponível para retirada.")
                return

            remaining = self.available_quantity - quantity
            self.quantity_hint.setText(
                f"Limite de retirada: {self.available_quantity} | "
                f"Quantidade restante: {remaining}"
            )
            return

        resulting = self.available_quantity + quantity
        self.quantity_hint.setText(f"Quantidade resultante após a entrada: {resulting}")

    def save(self) -> None:
        reason = self.reason_edit.text().strip()
        responsible = self.responsible_edit.text().strip()
        movement_type = self.type_combo.currentText()
        quantity = self.quantity_spin.value()

        if not reason or not responsible:
            QMessageBox.warning(
                self,
                "Campos obrigatórios",
                "Informe o motivo e o responsável pela movimentação.",
            )
            return

        if movement_type == "SAÍDA":
            if self.available_quantity <= 0:
                QMessageBox.warning(
                    self,
                    "Sem estoque disponível",
                    "Não é possível registrar uma saída para uma peça sem estoque.",
                )
                return
            if quantity > self.available_quantity:
                self.quantity_spin.setValue(self.available_quantity)
                QMessageBox.warning(
                    self,
                    "Quantidade indisponível",
                    "A quantidade de retirada não pode ser maior que o estoque disponível.",
                )
                return

        try:
            MovementRepository.create(
                part_id=int(self.part["id"]),
                movement_type=movement_type,
                quantity=quantity,
                reason=reason,
                responsible=responsible,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Movimentação não registrada", str(error))
            return

        self.movement_saved.emit()
        self.accept()
