from PyQt6.QtWidgets import QLineEdit, QListWidget, QVBoxLayout, QWidget

PLACEHOLDER_PATIENTS = [
    "001 — Burek (pies)",
    "002 — Mruczek (kot)",
    "003 — Kajtek (pies)",
    "004 — Luna (kot)",
    "005 — Reksio (pies)",
    "006 — Azor (pies)",
]


class PatientListPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(240)

        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("Szukaj pacjenta...")

        self._patient_list = QListWidget()
        self._patient_list.addItems(PLACEHOLDER_PATIENTS)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_field)
        layout.addWidget(self._patient_list)

        self._patient_list.setCurrentRow(0)
