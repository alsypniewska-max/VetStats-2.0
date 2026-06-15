from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from vetstats_app.analysis.patient_history import PatientHistoryCatalog, PatientListEntry


class PatientListPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(280)

        self._patient_list = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self._patient_list)

    def populate(self, catalog: PatientHistoryCatalog) -> None:
        self._patient_list.clear()
        if not catalog.is_success:
            item = QListWidgetItem(
                catalog.error_message or "Nie udało się wczytać listy pacjentów."
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._patient_list.addItem(item)
            return

        if not catalog.patients:
            item = QListWidgetItem("Brak pacjentów z prawidłowym patient_ID.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._patient_list.addItem(item)
            return

        for entry in catalog.patients:
            self._patient_list.addItem(self._create_item(entry))

    def connect_current_patient_changed(
        self,
        callback: Callable[[str | None], None],
    ) -> None:
        self._patient_list.currentItemChanged.connect(
            lambda current, _previous: callback(
                current.data(Qt.ItemDataRole.UserRole) if current is not None else None
            )
        )

    def clear_selection(self) -> None:
        self._patient_list.clearSelection()
        self._patient_list.setCurrentItem(None)

    @staticmethod
    def _create_item(entry: PatientListEntry) -> QListWidgetItem:
        item = QListWidgetItem(entry.label)
        item.setData(Qt.ItemDataRole.UserRole, entry.patient_id)
        return item
