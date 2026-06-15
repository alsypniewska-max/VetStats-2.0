from PyQt6.QtWidgets import QHBoxLayout, QWidget

from vetstats_app.services.patient_history_service import PatientHistoryService
from vetstats_app.ui.patient_history.patient_details_panel import PatientDetailsPanel
from vetstats_app.ui.patient_history.patient_list_panel import PatientListPanel


class PatientHistorySection(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._service = PatientHistoryService()
        self._patient_list_panel = PatientListPanel()
        self._patient_details_panel = PatientDetailsPanel()

        catalog = self._service.load_catalog()
        self._patient_list_panel.populate(catalog)

        layout = QHBoxLayout(self)
        layout.addWidget(self._patient_list_panel)
        layout.addWidget(self._patient_details_panel, stretch=1)

        self._patient_list_panel.connect_current_patient_changed(
            self._on_patient_selected
        )
        self._patient_list_panel.clear_selection()
        if not catalog.is_success:
            self._patient_details_panel.show_load_error(
                catalog.error_message
                or "Nie udało się wczytać danych historii pacjenta."
            )
        else:
            self._patient_details_panel.show_placeholder()

    def _on_patient_selected(self, patient_id: str | None) -> None:
        load_error = self._service.get_load_error()
        if load_error is not None:
            self._patient_details_panel.show_load_error(load_error)
            return

        if patient_id is None:
            self._patient_details_panel.show_placeholder()
            return

        detail = self._service.get_detail(patient_id)
        if detail is None:
            self._patient_details_panel.show_placeholder()
            return

        self._patient_details_panel.show_detail(detail)
