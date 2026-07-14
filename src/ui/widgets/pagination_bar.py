from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class PaginationBar(QWidget):
    page_changed = pyqtSignal(int)

    def __init__(self, page_size: int = 25, parent=None) -> None:
        super().__init__(parent)
        self.page_size = page_size
        self.current_page = 1
        self.total_pages = 1

        self.setObjectName("paginationBar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 11, 16, 11)
        self.layout.setSpacing(6)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("paginationSummary")
        self.layout.addWidget(self.summary_label)
        self.layout.addStretch()

        self.previous_button = self._button("‹", "Página anterior")
        self.previous_button.clicked.connect(
            lambda checked=False: self._request_page(self.current_page - 1)
        )
        self.layout.addWidget(self.previous_button)

        self.page_buttons: list[QPushButton] = []
        for _ in range(5):
            button = self._button("1", "Ir para a página")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, current_button=button: self._request_page(
                    int(current_button.property("pageNumber") or 1)
                )
            )
            self.page_buttons.append(button)
            self.layout.addWidget(button)

        self.next_button = self._button("›", "Próxima página")
        self.next_button.clicked.connect(
            lambda checked=False: self._request_page(self.current_page + 1)
        )
        self.layout.addWidget(self.next_button)

        self.set_state(1, 0)

    @staticmethod
    def _button(text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("paginationButton")
        button.setFixedSize(34, 32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        return button

    def set_state(self, current_page: int, total_items: int) -> None:
        self.total_pages = max(
            1,
            (max(total_items, 0) + self.page_size - 1) // self.page_size,
        )
        self.current_page = min(max(current_page, 1), self.total_pages)

        if total_items <= 0:
            self.summary_label.setText("0 REGISTROS")
        else:
            first_item = (self.current_page - 1) * self.page_size + 1
            last_item = min(self.current_page * self.page_size, total_items)
            self.summary_label.setText(
                f"{first_item}–{last_item} DE {total_items} REGISTROS"
            )

        self.previous_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
        self._update_page_buttons()
        self.setVisible(total_items > self.page_size)

    def _update_page_buttons(self) -> None:
        visible_count = min(5, self.total_pages)
        start_page = max(1, self.current_page - 2)
        end_page = min(self.total_pages, start_page + visible_count - 1)
        start_page = max(1, end_page - visible_count + 1)
        pages = list(range(start_page, end_page + 1))

        for index, button in enumerate(self.page_buttons):
            if index >= len(pages):
                button.hide()
                continue

            page_number = pages[index]
            button.setProperty("pageNumber", page_number)
            button.setText(str(page_number))
            button.setChecked(page_number == self.current_page)
            button.setToolTip(f"Ir para a página {page_number}")
            button.show()

    def _request_page(self, page: int) -> None:
        bounded_page = min(max(page, 1), self.total_pages)
        if bounded_page != self.current_page:
            self.page_changed.emit(bounded_page)
