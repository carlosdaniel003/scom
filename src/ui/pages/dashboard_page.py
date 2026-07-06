from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.repositories.movement_repository import MovementRepository
from src.repositories.part_repository import PartRepository
from src.ui.widgets.stat_card import StatCard


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 32)
        root.setSpacing(24)

        title = QLabel("Visão geral")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Acompanhe rapidamente a situação do inventário técnico.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.total_parts = StatCard("Peças cadastradas")
        self.total_quantity = StatCard("Quantidade física")
        self.low_stock = StatCard("Estoque baixo", object_name="warningCard")
        self.empty_stock = StatCard("Sem estoque", object_name="dangerCard")
        cards.addWidget(self.total_parts)
        cards.addWidget(self.total_quantity)
        cards.addWidget(self.low_stock)
        cards.addWidget(self.empty_stock)
        root.addLayout(cards)

        section = QLabel("Movimentações recentes")
        section.setObjectName("sectionTitle")
        root.addWidget(section)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Data e hora", "Código", "Peça", "Tipo", "Quantidade", "Responsável", "Motivo"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        totals = PartRepository.dashboard_totals()
        self.total_parts.set_value(totals["total_parts"])
        self.total_quantity.set_value(totals["total_quantity"])
        self.low_stock.set_value(totals["low_count"])
        self.empty_stock.set_value(totals["empty_count"])

        movements = MovementRepository.list_recent(10)
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
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
