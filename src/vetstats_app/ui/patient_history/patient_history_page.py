from PyQt6.QtWidgets import QHBoxLayout, QWidget

from vetstats_app.ui.patient_history.patient_details_panel import PatientDetailsPanel
from vetstats_app.ui.patient_history.patient_list_panel import PatientListPanel


class PatientHistoryPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        patient_list_panel = PatientListPanel()
        patient_details_panel = PatientDetailsPanel()

        layout = QHBoxLayout(self)
        layout.addWidget(patient_list_panel)
        layout.addWidget(patient_details_panel, stretch=1)
