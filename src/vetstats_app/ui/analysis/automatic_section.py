from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.ui.analysis.automatic_module_nav_panel import AutomaticModuleNavPanel
from vetstats_app.ui.analysis.diagnosis_culture_relationship_view import (
    DiagnosisCultureRelationshipView,
)
from vetstats_app.ui.analysis.diagnosis_frequency_view import DiagnosisFrequencyView
from vetstats_app.ui.analysis.microbiology_results_view import MicrobiologyResultsView
from vetstats_app.ui.analysis.patient_id_cross_table_summary_view import (
    PatientIdCrossTableSummaryView,
)
from vetstats_app.ui.analysis.population_characteristics_view import (
    PopulationCharacteristicsView,
)
from vetstats_app.ui.analysis.procedure_diagnosis_relationship_view import (
    ProcedureDiagnosisRelationshipView,
)
from vetstats_app.ui.analysis.resistance_over_time_view import ResistanceOverTimeView
from vetstats_app.ui.analysis.treatment_diagnosis_relationship_view import (
    TreatmentDiagnosisRelationshipView,
)
from vetstats_app.ui.analysis.treatment_groups_view import TreatmentGroupsView


class AutomaticAnalysisSection(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._report_service = AnalysisReportService()

        title_label = QLabel("Analiza automatyczna")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        combined_report_button = QPushButton("Generuj raport końcowy")
        combined_report_button.clicked.connect(self._on_generate_combined_report)

        header = QHBoxLayout()
        header.addWidget(title_label, stretch=1)
        header.addWidget(combined_report_button)

        module_nav_panel = AutomaticModuleNavPanel()

        module_stack = QStackedWidget()
        module_stack.addWidget(PopulationCharacteristicsView())
        module_stack.addWidget(DiagnosisFrequencyView())
        module_stack.addWidget(TreatmentGroupsView())
        module_stack.addWidget(MicrobiologyResultsView())
        module_stack.addWidget(ResistanceOverTimeView())
        module_stack.addWidget(DiagnosisCultureRelationshipView())
        module_stack.addWidget(ProcedureDiagnosisRelationshipView())
        module_stack.addWidget(TreatmentDiagnosisRelationshipView())
        module_stack.addWidget(PatientIdCrossTableSummaryView())

        body = QHBoxLayout()
        body.addWidget(module_nav_panel)
        body.addWidget(module_stack, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(body, stretch=1)

        module_nav_panel.connect_current_row_changed(module_stack.setCurrentIndex)
        module_nav_panel.set_current_row(0)

    def _on_generate_combined_report(self) -> None:
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Generuj raport końcowy",
            "final_automatic_analysis_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_final_automatic_analysis_report_pdf(
            Path(destination),
        )
        if error_message is not None:
            QMessageBox.warning(self, "Generuj raport końcowy", error_message)
            return

        QMessageBox.information(
            self,
            "Generuj raport końcowy",
            f"Zapisano raport PDF do pliku:\n{destination}",
        )
