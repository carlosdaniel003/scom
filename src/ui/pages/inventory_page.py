from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.repositories.part_repository import PartRepository
from src.ui.dialogs.edit_part_dialog import EditPartDialog
from src.ui.dialogs.movement_dialog import MovementDialog
from src.ui.dialogs.part_details_dialog import PartDetailsDialog


class InventoryPage(QWidget):
    inventory_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.status_filter = "all"

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 32)
        root.setSpacing(20)

        title = QLabel("Inventário")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Pesquise, filtre e movimente as peças cadastradas.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchInput")
        self.search_edit.setPlaceholderText(
            "Pesquisar por código, nome, descrição, categoria, modelo ou localização"
        )
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search_edit, 1)

        self.filter_group = QButtonGroup(self)
        filters = [
            ("Todas", "all"),
            ("Disponíveis", "available"),
            ("Estoque baixo", "low"),
            ("Sem estoque", "empty"),
        ]
        for label, value in filters:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("filterButton")
            if value == "all":
                button.setChecked(True)
            button.clicked.connect(
                lambda checked=False, filter_value=value: self.set_filter(filter_value)
            )
            self.filter_group.addButton(button)
            toolbar.addWidget(button)

        root.addLayout(toolbar)

        self.result_label = QLabel()
        self.result_label.setObjectName("mutedText")
        root.addWidget(self.result_label)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Código",
                "Peça",
                "Categoria",
                "Modelo",
                "Quantidade",
                "Mínimo",
                "Localização",
                "Status",
                "Ações",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 330)
        root.addWidget(self.table)

        self.refresh()

    def focus_search(self) -> None:
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def set_filter(self, value: str) -> None:
        self.status_filter = value
        self.refresh()

    def refresh(self) -> None:
        parts = PartRepository.search(self.search_edit.text(), self.status_filter)
        self.result_label.setText(f"{len(parts)} peça(s) encontrada(s)")
        self.table.setRowCount(len(parts))

        for row_index, part in enumerate(parts):
            fields = [
                part["internal_code"],
                part["name"],
                part["category_name"],
                part["model_name"] or "—",
                str(part["current_quantity"]),
                str(part["minimum_quantity"]),
                part["physical_location"],
                part["stock_status"],
            ]
            for column, value in enumerate(fields):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, part["id"])
                if column in {4, 5}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 7:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_colors = {
                        "Disponível": QColor("#6ee7b7"),
                        "Estoque baixo": QColor("#f6d365"),
                        "Sem estoque": QColor("#ff8093"),
                    }
                    item.setForeground(status_colors.get(value, QColor("#dce9f8")))
                self.table.setItem(row_index, column, item)

            action_widget = QWidget()
            actions = QHBoxLayout(action_widget)
            actions.setContentsMargins(4, 4, 4, 4)
            actions.setSpacing(5)

            view_button = QPushButton("Ver")
            edit_button = QPushButton("Editar")
            in_button = QPushButton("+ Entrada")
            out_button = QPushButton("- Saída")
            in_button.setObjectName("successButton")
            out_button.setObjectName("dangerButton")

            view_button.clicked.connect(
                lambda checked=False, part_id=int(part["id"]): self.open_details(part_id)
            )
            edit_button.clicked.connect(
                lambda checked=False, part_id=int(part["id"]): self.open_edit(part_id)
            )
            in_button.clicked.connect(
                lambda checked=False, part_id=int(part["id"]): self.open_movement(part_id, "ENTRADA")
            )
            out_button.clicked.connect(
                lambda checked=False, part_id=int(part["id"]): self.open_movement(part_id, "SAÍDA")
            )

            actions.addWidget(view_button)
            actions.addWidget(edit_button)
            actions.addWidget(in_button)
            actions.addWidget(out_button)
            self.table.setCellWidget(row_index, 8, action_widget)
            self.table.setRowHeight(row_index, 50)

    def open_details(self, part_id: int) -> None:
        part = PartRepository.get_by_id(part_id)
        if not part:
            return
        status = "Disponível"
        if part["current_quantity"] == 0:
            status = "Sem estoque"
        elif part["current_quantity"] <= part["minimum_quantity"]:
            status = "Estoque baixo"
        part["stock_status"] = status
        PartDetailsDialog(part, self).exec()

    def open_edit(self, part_id: int) -> None:
        part = PartRepository.get_by_id(part_id)
        if not part:
            return
        dialog = EditPartDialog(part, self)
        dialog.part_saved.connect(self.after_change)
        dialog.exec()

    def open_movement(self, part_id: int, movement_type: str) -> None:
        part = PartRepository.get_by_id(part_id)
        if not part:
            return
        dialog = MovementDialog(part, self, forced_type=movement_type)
        dialog.movement_saved.connect(self.after_change)
        dialog.exec()

    def after_change(self) -> None:
        self.refresh()
        self.inventory_changed.emit()
