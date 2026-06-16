from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.services.preview_data_service import PreviewDatasetSnapshot


def _configure_preview_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)


def _populate_preview_table(table: QTableWidget, snapshot: PreviewDatasetSnapshot) -> None:
    frame = snapshot.display_frame()
    columns = [str(column) for column in frame.columns]

    table.clear()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setRowCount(len(frame))

    for row_index in range(len(frame)):
        for column_index, column_name in enumerate(frame.columns):
            value = frame.iloc[row_index, column_index]
            table.setItem(
                row_index,
                column_index,
                QTableWidgetItem("" if value is None else str(value)),
            )

    table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    table.horizontalHeader().setStretchLastSection(True)


class TablePreviewPanel(QWidget):
    def __init__(
        self,
        snapshot: PreviewDatasetSnapshot,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        title_label = QLabel(snapshot.table_name)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if snapshot.source_path is not None:
            source_label = QLabel(f"Źródło: {snapshot.source_path}")
        else:
            source_label = QLabel(f"Plik: {snapshot.file_name}")
        source_label.setWordWrap(True)

        self._table = QTableWidget()
        _configure_preview_table(self._table)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title_label)
        layout.addWidget(source_label)

        if snapshot.is_loaded:
            _populate_preview_table(self._table, snapshot)
            layout.addWidget(self._table, stretch=1)
            return

        error_label = QLabel(snapshot.error_message or "Brak danych do podglądu.")
        error_label.setWordWrap(True)
        layout.addWidget(error_label)
        layout.addStretch()
