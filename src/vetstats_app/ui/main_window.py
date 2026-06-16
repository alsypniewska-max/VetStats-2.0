from PyQt6.QtWidgets import QMainWindow, QTabWidget

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
        tabs.addTab(PreviewPage(), "Preview")
        tabs.addTab(AnalysisPage(), "Analysis")
        tabs.addTab(PatientHistorySection(), "Patient History")
        tabs.addTab(LogsSection(), "Logs")
        tabs.addTab(ReportPage(), "Report")

        self.setCentralWidget(tabs)
