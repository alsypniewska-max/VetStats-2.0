from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from vetstats_app.ui.analysis.breed_treatment_duration_view import (
    BreedTreatmentDurationView,
)
from vetstats_app.ui.analysis.ulcer_breed_treatment_duration_view import (
    UlcerBreedTreatmentDurationView,
)
from vetstats_app.ui.analysis.diagnosis_culture_relationship_view import (
    DiagnosisCultureRelationshipView,
)
from vetstats_app.ui.analysis.diagnosis_frequency_view import DiagnosisFrequencyView
from vetstats_app.ui.analysis.duration_of_problem_stats_view import (
    DurationOfProblemStatsView,
)
from vetstats_app.ui.analysis.micro_monthly_distribution_view import (
    MicroMonthlyDistributionView,
)
from vetstats_app.ui.analysis.pre_swab_drugs_view import PreSwabDrugsView
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

        self._module_stack = QStackedWidget()
        self._action_bar_stack = QStackedWidget()

        module_views = (
            PopulationCharacteristicsView(),
            DiagnosisFrequencyView(),
            TreatmentGroupsView(),
            MicrobiologyResultsView(),
            ResistanceOverTimeView(),
            DiagnosisCultureRelationshipView(),
            ProcedureDiagnosisRelationshipView(),
            TreatmentDiagnosisRelationshipView(),
            BreedTreatmentDurationView(),
            UlcerBreedTreatmentDurationView(),
            DurationOfProblemStatsView(),
            MicroMonthlyDistributionView(),
            PreSwabDrugsView(),
            PatientIdCrossTableSummaryView(),
        )
        for view in module_views:
            self._module_stack.addWidget(view)
            self._action_bar_stack.addWidget(view.action_bar_widget())
            for scroll_area in view.findChildren(QScrollArea):
                scroll_area.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOn
                )
                scroll_area.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._module_stack, stretch=1)

    @property
    def action_bar_stack(self) -> QStackedWidget:
        return self._action_bar_stack

    def set_current_module(self, index: int) -> None:
        self._module_stack.setCurrentIndex(index)
        self._action_bar_stack.setCurrentIndex(index)
