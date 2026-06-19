from collections.abc import Callable

from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QWidget

AUTOMATIC_MODULE_LABELS = [
    "Charakterystyka populacji pacjentów",
    "Analiza częstości rozpoznań",
    "Analiza leczenia w grupach pacjentów",
    "Analiza wyników mikrobiologicznych",
    "Analiza oporności bakterii w czasie",
    "Powiązanie rozpoznań z posiewem",
    "Analiza zależności między zabiegiem a rozpoznaniem",
    "Powiązanie leczenia z typem wrzodu",
    "Czas trwania problemu przed pierwszą wizytą",
    "Rozkład wymazów w miesiącach i latach",
    "Leki stosowane przed wymazem",
    "Powiązania patient_ID między tabelami",
]


class AutomaticModuleNavPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(280)

        self._module_list = QListWidget()
        self._module_list.addItems(AUTOMATIC_MODULE_LABELS)

        layout = QVBoxLayout(self)
        layout.addWidget(self._module_list)

        self.set_current_row(0)

    def connect_current_row_changed(self, callback: Callable[[int], None]) -> None:
        self._module_list.currentRowChanged.connect(callback)

    def set_current_row(self, row: int) -> None:
        self._module_list.setCurrentRow(row)
