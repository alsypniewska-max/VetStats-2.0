from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from vetstats_app.ui.preview.summary_panel import SummaryPanel
from vetstats_app.ui.preview.table_nav_panel import TABLE_NAMES, TableNavPanel
from vetstats_app.ui.preview.table_preview_panel import TablePreviewPanel


class PreviewPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        summary_panel = SummaryPanel()
        table_nav_panel = TableNavPanel()

        table_preview_stack = QStackedWidget()
        for table_name in TABLE_NAMES:
            table_preview_stack.addWidget(TablePreviewPanel(table_name))

        body = QHBoxLayout()
        body.addWidget(table_nav_panel)
        body.addWidget(table_preview_stack, stretch=1)

        layout = QVBoxLayout(self)
        layout.addWidget(summary_panel)
        layout.addLayout(body)

        table_nav_panel._table_list.currentRowChanged.connect(
            table_preview_stack.setCurrentIndex
        )
        table_nav_panel._table_list.setCurrentRow(0)
