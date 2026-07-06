from PyQt6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget

from vetstats_app.services.branding import footer_text
from vetstats_app.ui.analysis.analysis_page import AnalysisPage
from vetstats_app.ui.logs.logs_page import LogsSection
from vetstats_app.ui.patient_history.patient_history_page import PatientHistorySection
from vetstats_app.ui.preview.preview_page import PreviewPage
from vetstats_app.ui.report.report_page import ReportPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VetStats 2.0")
        self.setMinimumSize(900, 600)

        tabs = QTabWidget()
        analysis_page = AnalysisPage()
        tabs.addTab(PreviewPage(), "Preview")
        tabs.addTab(analysis_page, "Analysis")
        tabs.addTab(PatientHistorySection(), "Patient History")
        tabs.addTab(LogsSection(detailed_context_provider=analysis_page.detailed_analysis_context), "Logs")
        tabs.addTab(ReportPage(detailed_context_provider=analysis_page.detailed_analysis_context), "Report")

        self.setCentralWidget(tabs)
        _configure_app_status_bar(self)


def _configure_app_status_bar(main_window: QMainWindow) -> None:
    status_bar = QStatusBar(main_window)
    status_bar.setSizeGripEnabled(False)
    status_bar.setStyleSheet(
        "QStatusBar {"
        "  border-top: 1px solid #E5E7EB;"
        "  background: #F9FAFB;"
        "  color: #6B7280;"
        "}"
        "QStatusBar::item { border: none; }"
    )
    main_window.setStatusBar(status_bar)

    copyright_label = QLabel(footer_text())
    copyright_label.setStyleSheet("color: #6B7280;")
    status_bar.addPermanentWidget(copyright_label)
