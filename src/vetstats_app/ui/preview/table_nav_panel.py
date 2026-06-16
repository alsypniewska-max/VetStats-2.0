from collections.abc import Callable

from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QWidget

TABLE_NAMES = [
    "patient",
    "clinical",
    "micro",
]


class TableNavPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(200)

        self._table_list = QListWidget()
        self._table_list.addItems(TABLE_NAMES)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table_list)

        self._table_list.setCurrentRow(0)

    def connect_current_row_changed(self, callback: Callable[[int], None]) -> None:
        self._table_list.currentRowChanged.connect(callback)

    def set_current_row(self, row: int) -> None:
        self._table_list.setCurrentRow(row)
