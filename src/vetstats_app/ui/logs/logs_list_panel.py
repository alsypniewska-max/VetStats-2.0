from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.logs import LogsCatalog

COLUMN_HEADERS = ("timestamp", "level", "source", "message")


class LogsListPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(520)

        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMN_HEADERS))
        self._table.setHorizontalHeaderLabels(list(COLUMN_HEADERS))
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)

    def populate(self, catalog: LogsCatalog) -> None:
        self._table.clearContents()
        self._table.setRowCount(0)
        self._table.clearSpans()

        if not catalog.is_success and not catalog.entries:
            self._table.setRowCount(1)
            item = QTableWidgetItem(
                catalog.error_message or "Nie udało się wczytać logów."
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._table.setItem(0, 0, item)
            self._table.setSpan(0, 0, 1, len(COLUMN_HEADERS))
            return

        if not catalog.entries:
            self._table.setRowCount(1)
            item = QTableWidgetItem("Brak wpisów logów.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._table.setItem(0, 0, item)
            self._table.setSpan(0, 0, 1, len(COLUMN_HEADERS))
            return

        self._table.setRowCount(len(catalog.entries))
        for row_index, entry in enumerate(catalog.entries):
            self._table.setItem(row_index, 0, self._create_item(entry.timestamp, entry.id))
            self._table.setItem(row_index, 1, self._create_item(entry.level, entry.id))
            self._table.setItem(row_index, 2, self._create_item(entry.source, entry.id))
            self._table.setItem(row_index, 3, self._create_item(entry.message, entry.id))

    def connect_current_log_entry_changed(
        self,
        callback: Callable[[str | None], None],
    ) -> None:
        self._table.itemSelectionChanged.connect(
            lambda: callback(self._current_entry_id())
        )

    def clear_selection(self) -> None:
        self._table.clearSelection()
        self._table.setCurrentItem(None)

    def _current_entry_id(self) -> str | None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        row_index = selected_rows[0].row()
        item = self._table.item(row_index, 0)
        if item is None:
            return None

        entry_id = item.data(Qt.ItemDataRole.UserRole)
        return str(entry_id) if entry_id else None

    @staticmethod
    def _create_item(value: str, entry_id: str) -> QTableWidgetItem:
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setData(Qt.ItemDataRole.UserRole, entry_id)
        return item
