from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

SOURCE_FILES = [
    "patient.csv",
    "clinical.csv",
    "micro.csv",
]

TABLE_STATS = [
    "patient: 120 wierszy, 15 kolumn",
    "clinical: 340 wierszy, 12 kolumn",
    "micro: 890 wierszy, 18 kolumn",
]

DATA_STATUS = "Status: dane placeholder — brak rzeczywistego wczytywania"


class SummaryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        group = QGroupBox("Podsumowanie danych")
        group_layout = QVBoxLayout(group)

        source_label = QLabel("Wczytane pliki źródłowe:")
        group_layout.addWidget(source_label)
        for filename in SOURCE_FILES:
            group_layout.addWidget(QLabel(f"  • {filename}"))

        group_layout.addWidget(QLabel("Liczba wierszy i kolumn:"))
        for stats in TABLE_STATS:
            group_layout.addWidget(QLabel(f"  • {stats}"))

        group_layout.addWidget(QLabel(DATA_STATUS))

        layout = QVBoxLayout(self)
        layout.addWidget(group)
