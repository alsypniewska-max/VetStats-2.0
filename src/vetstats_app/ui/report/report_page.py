from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from vetstats_app.ui.report.report_metadata_panel import ReportMetadataPanel
from vetstats_app.ui.report.report_structure_panel import ReportStructurePanel


class ReportPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        generate_pdf_button = QPushButton("Generuj raport PDF")

        action_bar = QHBoxLayout()
        action_bar.addWidget(generate_pdf_button)
        action_bar.addStretch()

        report_metadata_panel = ReportMetadataPanel()
        report_structure_panel = ReportStructurePanel()

        layout = QVBoxLayout(self)
        layout.addLayout(action_bar)
        layout.addWidget(report_metadata_panel)
        layout.addWidget(report_structure_panel, stretch=1)
