from PyQt6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.repositories.movement_repository import MovementRepository


class MovementsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 32)
        root.setSpacing(20)

        title = QLabel("Histórico de movimentações")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Registro de todas as entradas e saídas do inventário.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.table = QTableWidget(0, 9)
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
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        movements = MovementRepository.list_recent(500)
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
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
