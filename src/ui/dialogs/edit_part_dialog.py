import sqlite3

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QVBoxLayout

from src.models.part import PartInput
from src.repositories.part_repository import PartRepository
from src.services.image_service import store_part_image
from src.ui.pages.registration_page import PartForm


class EditPartDialog(QDialog):
    part_saved = pyqtSignal()

    def __init__(self, part: dict, parent=None) -> None:
        super().__init__(parent)
        self.part = part
        self.setWindowTitle("Editar peça")
        self.setMinimumSize(850, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        self.form = PartForm(show_initial_quantity=False)
        self.form.load_part(part)
        root.addWidget(self.form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salvar alterações")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def save(self) -> None:
        try:
            data = self.form.collect_data()
            image_path = store_part_image(data.image_path)
            existing_path = self.part.get("image_path")
            data = PartInput(
                internal_code=data.internal_code,
                name=data.name,
                description=data.description,
                category_id=data.category_id,
                component_value=data.component_value,
                component_unit=data.component_unit,
                model_name=data.model_name,
                current_quantity=int(self.part["current_quantity"]),
                minimum_quantity=data.minimum_quantity,
                physical_location=data.physical_location,
                notes=data.notes,
                image_path=image_path or existing_path,
            )
            PartRepository.update(int(self.part["id"]), data)
        except (ValueError, sqlite3.IntegrityError) as error:
            message = str(error)
            if "UNIQUE constraint failed: parts.internal_code" in message:
                message = "Já existe uma peça cadastrada com esse código interno."
            QMessageBox.warning(self, "Não foi possível salvar", message)
            return

        self.part_saved.emit()
        self.accept()
