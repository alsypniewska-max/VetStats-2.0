from collections.abc import Callable

from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QWidget

SECTION_LABELS = [
    "Analiza automatyczna",
    "Analiza szczegółowa",
]


class SectionNavPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(200)

        self._section_list = QListWidget()
        self._section_list.addItems(SECTION_LABELS)

        layout = QVBoxLayout(self)
        layout.addWidget(self._section_list)

        self.set_current_row(0)

    def connect_current_row_changed(self, callback: Callable[[int], None]) -> None:
        self._section_list.currentRowChanged.connect(callback)

    def set_current_row(self, row: int) -> None:
        self._section_list.setCurrentRow(row)
