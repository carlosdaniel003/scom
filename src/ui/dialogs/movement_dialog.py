from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from src.repositories.movement_repository import MovementRepository


class MovementDialog(QDialog):
    movement_saved = pyqtSignal()

    def __init__(self, part: dict, parent=None, forced_type: str | None = None) -> None:
        super().__init__(parent)
        self.part = part
        self.setWindowTitle("Movimentação de estoque")
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        title = QLabel(f"{part['internal_code']} — {part['name']}")
        title.setObjectName("dialogTitle")
        available = QLabel(f"Quantidade disponível: {part['current_quantity']}")
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
        self.quantity_spin.setRange(1, 1_000_000)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Ex.: Reposição, manutenção, consumo em reparo")

        self.responsible_edit = QLineEdit()
        self.responsible_edit.setPlaceholderText("Nome do responsável")

        form.addRow("Tipo", self.type_combo)
        form.addRow("Quantidade", self.quantity_spin)
        form.addRow("Motivo", self.reason_edit)
        form.addRow("Responsável", self.responsible_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Registrar")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def save(self) -> None:
        reason = self.reason_edit.text().strip()
        responsible = self.responsible_edit.text().strip()
        if not reason or not responsible:
            QMessageBox.warning(
                self,
                "Campos obrigatórios",
                "Informe o motivo e o responsável pela movimentação.",
            )
            return

        try:
            MovementRepository.create(
                part_id=int(self.part["id"]),
                movement_type=self.type_combo.currentText(),
                quantity=self.quantity_spin.value(),
                reason=reason,
                responsible=responsible,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Movimentação não registrada", str(error))
            return

        self.movement_saved.emit()
        self.accept()
