from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from vetstats_app.ui.analysis.automatic_module_nav_panel import AutomaticModuleNavPanel
from vetstats_app.ui.analysis.diagnosis_culture_relationship_view import (
    DiagnosisCultureRelationshipView,
)
from vetstats_app.ui.analysis.diagnosis_frequency_view import DiagnosisFrequencyView
from vetstats_app.ui.analysis.microbiology_results_view import MicrobiologyResultsView
from vetstats_app.ui.analysis.population_characteristics_view import (
    PopulationCharacteristicsView,
)
from vetstats_app.ui.analysis.procedure_diagnosis_relationship_view import (
    ProcedureDiagnosisRelationshipView,
)
from vetstats_app.ui.analysis.resistance_over_time_view import ResistanceOverTimeView
from vetstats_app.ui.analysis.treatment_groups_view import TreatmentGroupsView


class AutomaticAnalysisSection(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title_label = QLabel("Analiza automatyczna")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        module_nav_panel = AutomaticModuleNavPanel()

        module_stack = QStackedWidget()
        module_stack.addWidget(PopulationCharacteristicsView())
        module_stack.addWidget(DiagnosisFrequencyView())
        module_stack.addWidget(TreatmentGroupsView())
        module_stack.addWidget(MicrobiologyResultsView())
        module_stack.addWidget(ResistanceOverTimeView())
        module_stack.addWidget(DiagnosisCultureRelationshipView())
        module_stack.addWidget(ProcedureDiagnosisRelationshipView())

        body = QHBoxLayout()
        body.addWidget(module_nav_panel)
        body.addWidget(module_stack, stretch=1)

        layout = QVBoxLayout(self)
        layout.addWidget(title_label)
        layout.addLayout(body, stretch=1)

        module_nav_panel.connect_current_row_changed(module_stack.setCurrentIndex)
        module_nav_panel.set_current_row(0)
