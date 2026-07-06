from PyQt6.QtCore import QSize, Qt
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

from src.repositories.movement_repository import MovementRepository
from src.ui.widgets.compact_metric import CompactMetric
from src.ui.widgets.page_header import PageHeader, SectionHeader
from src.utils.paths import resource_path


class MovementsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.movement_filter = "all"
        self.all_movements: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 30)
        root.setSpacing(18)

        header = PageHeader(
            "Movimentações",
            "Acompanhe a rastreabilidade de todas as entradas e saídas do inventário.",
            "history.svg",
            "RASTREABILIDADE",
        )
        root.addWidget(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.total_metric = CompactMetric("Movimentações registradas", "history.svg")
        self.entry_metric = CompactMetric("Entradas", "entry.svg", "compactMetricSuccess")
        self.exit_metric = CompactMetric("Saídas", "withdrawal.svg", "compactMetricDanger")
        metrics.addWidget(self.total_metric)
        metrics.addWidget(self.entry_metric)
        metrics.addWidget(self.exit_metric)
        root.addLayout(metrics)

        filter_panel = QFrame()
        filter_panel.setObjectName("toolbarPanel")
        filter_layout = QHBoxLayout(filter_panel)
        filter_layout.setContentsMargins(16, 14, 16, 14)
        filter_layout.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchInput")
        self.search_edit.setPlaceholderText(
            "Pesquisar por código, peça, responsável, motivo, tipo ou data"
        )
        self.search_edit.addAction(
            QIcon(str(resource_path("icons", "search.svg"))),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search_edit.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_edit, 1)

        filter_label = QLabel("TIPO")
        filter_label.setObjectName("toolbarLabel")
        filter_layout.addWidget(filter_label)

        self.filter_group = QButtonGroup(self)
        filters = [
            ("Todas", "all", "list.svg"),
            ("Entradas", "ENTRADA", "entry.svg"),
            ("Saídas", "SAÍDA", "withdrawal.svg"),
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
            "Histórico de movimentações",
            "Registros ordenados da movimentação mais recente para a mais antiga.",
            "history.svg",
        )
        self.result_label = QLabel()
        self.result_label.setObjectName("resultBadge")
        section_header.add_trailing_widget(self.result_label)
        data_layout.addWidget(section_header)

        self.table = QTableWidget(0, 9)
        self.table.setObjectName("movementsTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Data e hora",
                "Código",
                "Peça",
                "Tipo",
                "Quantidade",
                "Anterior",
                "Resultante",
                "Responsável",
                "Motivo",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        table_header = self.table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        table_header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        data_layout.addWidget(self.table, 1)

        root.addWidget(data_panel, 1)
        self.refresh()

    def set_filter(self, value: str) -> None:
        self.movement_filter = value
        self.apply_filters()

    def refresh(self) -> None:
        self.all_movements = MovementRepository.list_recent(500)
        entries = sum(1 for movement in self.all_movements if movement["movement_type"] == "ENTRADA")
        exits = sum(1 for movement in self.all_movements if movement["movement_type"] == "SAÍDA")
        self.total_metric.set_value(len(self.all_movements))
        self.entry_metric.set_value(entries)
        self.exit_metric.set_value(exits)
        self.apply_filters()

    def apply_filters(self) -> None:
        query = self.search_edit.text().strip().lower()
        movements = []

        for movement in self.all_movements:
            if self.movement_filter != "all" and movement["movement_type"] != self.movement_filter:
                continue

            searchable = " ".join(
                str(movement.get(field) or "")
                for field in (
                    "created_at",
                    "internal_code",
                    "part_name",
                    "movement_type",
                    "responsible",
                    "reason",
                )
            ).lower()
            if query and query not in searchable:
                continue
            movements.append(movement)

        self.result_label.setText(f"{len(movements)} REGISTRO(S)")
        self.table.clearSpans()

        if not movements:
            self.table.setRowCount(1)
            empty_item = QTableWidgetItem(
                "Nenhuma movimentação encontrada para os critérios selecionados."
            )
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty_item)
            self.table.setSpan(0, 0, 1, 9)
            self.table.setRowHeight(0, 110)
            return

        self.table.setRowCount(len(movements))
        for row_index, movement in enumerate(movements):
            values = [
                movement["created_at"],
                movement["internal_code"],
                movement["part_name"],
                movement["movement_type"],
                str(movement["quantity"]),
                str(movement["previous_quantity"]),
                str(movement["resulting_quantity"]),
                movement["responsible"],
                movement["reason"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {3, 4, 5, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    if value == "ENTRADA":
                        item.setForeground(QColor("#6ee7b7"))
                        item.setIcon(QIcon(str(resource_path("icons", "entry.svg"))))
                    else:
                        item.setForeground(QColor("#ff8093"))
                        item.setIcon(QIcon(str(resource_path("icons", "withdrawal.svg"))))
                self.table.setItem(row_index, column, item)
            self.table.setRowHeight(row_index, 48)
