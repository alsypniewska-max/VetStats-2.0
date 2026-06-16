from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView, QSizePolicy, QTableWidget


def configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)
    table.verticalHeader().setVisible(False)
    table.setWordWrap(True)
    table.setAlternatingRowColors(True)
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)


def finalize_reference_table(table: QTableWidget) -> None:
    table.resizeRowsToContents()

    header = table.horizontalHeader()
    for column_index in range(table.columnCount()):
        if header.sectionResizeMode(column_index) != QHeaderView.ResizeMode.Stretch:
            table.resizeColumnToContents(column_index)

    height = table.horizontalHeader().height()
    for row_index in range(table.rowCount()):
        height += table.rowHeight(row_index)
    height += 2 * table.frameWidth()
    if table.rowCount() == 0:
        height += table.fontMetrics().height() + 8

    table.setMinimumHeight(height)


def stretch_column(table: QTableWidget, column_index: int) -> None:
    table.horizontalHeader().setSectionResizeMode(
        column_index,
        QHeaderView.ResizeMode.Stretch,
    )
