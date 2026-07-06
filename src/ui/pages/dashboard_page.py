from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.repositories.movement_repository import MovementRepository
from src.repositories.part_repository import PartRepository
from src.ui.widgets.stat_card import StatCard


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dashboardPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 30)
        root.setSpacing(20)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        title = QLabel("Visão geral")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Panorama operacional do estoque técnico em tempo real.")
        subtitle.setObjectName("pageSubtitle")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()

        status_chip = QLabel("●  INVENTÁRIO LOCAL")
        status_chip.setObjectName("liveStatusChip")
        header.addWidget(status_chip, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.total_parts = StatCard(
            "Peças cadastradas",
            icon_name="package.svg",
            helper_text="Itens únicos no catálogo",
        )
        self.total_quantity = StatCard(
            "Quantidade física",
            icon_name="layers.svg",
            helper_text="Soma de todas as unidades",
        )
        self.low_stock = StatCard(
            "Estoque baixo",
            object_name="warningCard",
            icon_name="warning.svg",
            helper_text="Requer atenção de reposição",
        )
        self.empty_stock = StatCard(
            "Sem estoque",
            object_name="dangerCard",
            icon_name="empty.svg",
            helper_text="Itens indisponíveis",
        )
        cards.addWidget(self.total_parts)
        cards.addWidget(self.total_quantity)
        cards.addWidget(self.low_stock)
        cards.addWidget(self.empty_stock)
        root.addLayout(cards)

        activity_panel = QFrame()
        activity_panel.setObjectName("activityPanel")
        panel_layout = QVBoxLayout(activity_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        section_header = QFrame()
        section_header.setObjectName("sectionHeader")
        section_layout = QHBoxLayout(section_header)
        section_layout.setContentsMargins(20, 16, 20, 14)
        section_layout.setSpacing(12)

        section_icon = QLabel("↕")
        section_icon.setObjectName("sectionIcon")
        section_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section_icon.setFixedSize(34, 34)

        section_text = QVBoxLayout()
        section_text.setSpacing(2)
        section = QLabel("Movimentações recentes")
        section.setObjectName("sectionTitle")
        section_subtitle = QLabel("Últimas entradas e saídas registradas no sistema")
        section_subtitle.setObjectName("sectionSubtitle")
        section_text.addWidget(section)
        section_text.addWidget(section_subtitle)

        section_layout.addWidget(section_icon)
        section_layout.addLayout(section_text)
        section_layout.addStretch()
        panel_layout.addWidget(section_header)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("dashboardTable")
        self.table.setHorizontalHeaderLabels(
            ["Data e hora", "Código", "Peça", "Tipo", "Quantidade", "Responsável", "Motivo"]
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
        table_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        panel_layout.addWidget(self.table, 1)

        root.addWidget(activity_panel, 1)
        self.refresh()

    def refresh(self) -> None:
        totals = PartRepository.dashboard_totals()
        self.total_parts.set_value(totals["total_parts"])
        self.total_quantity.set_value(totals["total_quantity"])
        self.low_stock.set_value(totals["low_count"])
        self.empty_stock.set_value(totals["empty_count"])

        movements = MovementRepository.list_recent(10)
        self.table.clearSpans()

        if not movements:
            self.table.setRowCount(1)
            empty_item = QTableWidgetItem(
                "Nenhuma movimentação registrada. As entradas e saídas aparecerão aqui."
            )
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty_item)
            self.table.setSpan(0, 0, 1, 7)
            self.table.setRowHeight(0, 96)
            return

        self.table.setRowCount(len(movements))
        for row_index, movement in enumerate(movements):
            values = [
                movement["created_at"],
                movement["internal_code"],
                movement["part_name"],
                movement["movement_type"],
                str(movement["quantity"]),
                movement["responsible"],
                movement["reason"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {3, 4}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_index, column, item)
            self.table.setRowHeight(row_index, 46)
