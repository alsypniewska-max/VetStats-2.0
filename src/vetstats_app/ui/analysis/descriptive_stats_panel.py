from PyQt6.QtWidgets import QGroupBox, QTableWidget, QTableWidgetItem, QVBoxLayout

from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
    stretch_column,
)


def build_descriptive_stats_panel(block: ReportTableBlock) -> QGroupBox:
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)

    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    configure_reference_table(table)
    if len(block.columns) > 1:
        stretch_column(table, 0)

    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    finalize_reference_table(table)
    layout.addWidget(table)
    return group
