from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from vetstats_app.ui.logs.log_entries_panel import LogEntriesPanel
from vetstats_app.ui.logs.log_summary_panel import LogSummaryPanel


class LogsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        export_report_button = QPushButton("Eksport raportu")

        action_bar = QHBoxLayout()
        action_bar.addWidget(export_report_button)
        action_bar.addStretch()

        log_summary_panel = LogSummaryPanel()
        log_entries_panel = LogEntriesPanel()

        layout = QVBoxLayout(self)
        layout.addLayout(action_bar)
        layout.addWidget(log_summary_panel)
        layout.addWidget(log_entries_panel, stretch=1)
