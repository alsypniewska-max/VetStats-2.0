from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

COLUMN_HEADERS = [
    "Data",
    "Godzina",
    "Typ",
    "Wiadomość",
]

PLACEHOLDER_ENTRIES = [
    ("15.06.2026", "09:00:01", "INFO", "Aplikacja VetStats 2.0 uruchomiona."),
    ("15.06.2026", "09:00:02", "INFO", "Oczekiwanie na wczytanie danych."),
    ("15.06.2026", "09:00:05", "WARNING", "Brak wczytanych plików CSV — dane placeholder."),
    ("15.06.2026", "09:00:06", "INFO", "Podgląd danych: tryb placeholder aktywny."),
    ("15.06.2026", "09:00:10", "ERROR", "Walidacja danych: nie uruchomiono (placeholder)."),
    ("15.06.2026", "09:00:12", "INFO", "Sesja gotowa do dalszej pracy."),
]


class LogEntriesPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMN_HEADERS))
        self._table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self._table.setRowCount(len(PLACEHOLDER_ENTRIES))
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )

        for row, (date, time, log_type, message) in enumerate(PLACEHOLDER_ENTRIES):
            self._table.setItem(row, 0, QTableWidgetItem(date))
            self._table.setItem(row, 1, QTableWidgetItem(time))
            self._table.setItem(row, 2, QTableWidgetItem(log_type))
            self._table.setItem(row, 3, QTableWidgetItem(message))

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
