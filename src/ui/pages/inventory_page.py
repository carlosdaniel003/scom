from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
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
from src.ui.widgets.page_header import PageHeader, SectionHeader
from src.utils.paths import resource_path


class InventoryPage(QWidget):
    inventory_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.status_filter = "all"

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 30)
        root.setSpacing(18)

        header = PageHeader(
            "Inventário e pesquisa",
            "Localize, filtre e movimente as peças cadastradas no estoque técnico.",
            "inventory.svg",
            "CATÁLOGO TÉCNICO",
        )
        root.addWidget(header)

        filter_panel = QFrame()
        filter_panel.setObjectName("toolbarPanel")
        filter_layout = QHBoxLayout(filter_panel)
        filter_layout.setContentsMargins(16, 14, 16, 14)
        filter_layout.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchInput")
        self.search_edit.setPlaceholderText(
            "Pesquisar por código, nome, descrição, categoria, modelo ou localização"
        )
        self.search_edit.addAction(
            QIcon(str(resource_path("icons", "search.svg"))),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search_edit.textChanged.connect(self.refresh)
        filter_layout.addWidget(self.search_edit, 1)

        filter_label = QLabel("FILTRAR POR")
        filter_label.setObjectName("toolbarLabel")
        filter_layout.addWidget(filter_label)

        self.filter_group = QButtonGroup(self)
        filters = [
            ("Todas", "all", "list.svg"),
            ("Disponíveis", "available", "check.svg"),
            ("Estoque baixo", "low", "warning.svg"),
            ("Sem estoque", "empty", "empty.svg"),
        ]
        for label, value, icon_name in filters:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("filterButton")
            button.setIcon(QIcon(str(resource_path("icons", icon_name))))
            button.setIconSize(QSize(16, 16))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if value == "all":
                button.setChecked(True)
            button.clicked.connect(
                lambda checked=False, filter_value=value: self.set_filter(filter_value)
            )
            self.filter_group.addButton(button)
            filter_layout.addWidget(button)

        root.addWidget(filter_panel)

        data_panel = QFrame()
        data_panel.setObjectName("dataPanel")
        data_layout = QVBoxLayout(data_panel)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(0)

        section_header = SectionHeader(
            "Catálogo de peças",
            "Visualize dados, status e ações de cada item cadastrado.",
            "package.svg",
        )
        self.result_label = QLabel()
        self.result_label.setObjectName("resultBadge")
        section_header.add_trailing_widget(self.result_label)
        data_layout.addWidget(section_header)

        self.table = QTableWidget(0, 9)
        self.table.setObjectName("inventoryTable")
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
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 350)
        data_layout.addWidget(self.table, 1)

        root.addWidget(data_panel, 1)
        self.refresh()

    def focus_search(self) -> None:
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def set_filter(self, value: str) -> None:
        self.status_filter = value
        self.refresh()

    def refresh(self) -> None:
        parts = PartRepository.search(self.search_edit.text(), self.status_filter)
        self.result_label.setText(f"{len(parts)} RESULTADO(S)")
        self.table.clearSpans()

        if not parts:
            self.table.setRowCount(1)
            empty_item = QTableWidgetItem(
                "Nenhuma peça encontrada. Ajuste a pesquisa ou os filtros para continuar."
            )
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty_item)
            self.table.setSpan(0, 0, 1, 9)
            self.table.setRowHeight(0, 110)
            return

        self.table.setRowCount(len(parts))
        status_icons = {
            "Disponível": "check.svg",
            "Estoque baixo": "warning.svg",
            "Sem estoque": "empty.svg",
        }
        status_colors = {
            "Disponível": QColor("#6ee7b7"),
            "Estoque baixo": QColor("#f6d365"),
            "Sem estoque": QColor("#ff8093"),
        }

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
                if column in {4, 5, 7}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 7:
                    item.setForeground(status_colors.get(value, QColor("#dce9f8")))
                    icon_name = status_icons.get(value)
                    if icon_name:
                        item.setIcon(QIcon(str(resource_path("icons", icon_name))))
                self.table.setItem(row_index, column, item)

            action_widget = QWidget()
            action_widget.setObjectName("tableActions")
            actions = QHBoxLayout(action_widget)
            actions.setContentsMargins(5, 4, 5, 4)
            actions.setSpacing(5)

            view_button = self._action_button("Ver", "view.svg", "tableActionButton")
            edit_button = self._action_button("Editar", "edit.svg", "tableActionButton")
            in_button = self._action_button("Entrada", "arrow-in.svg", "successButton")
            out_button = self._action_button("Saída", "arrow-out.svg", "dangerButton")

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
            self.table.setRowHeight(row_index, 54)

    @staticmethod
    def _action_button(text: str, icon_name: str, object_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setIcon(QIcon(str(resource_path("icons", icon_name))))
        button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

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
