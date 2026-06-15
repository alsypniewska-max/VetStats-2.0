from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

SECTION_TITLE = "Analiza automatyczna — raport podsumowujący"
SOURCE_DATA = "patient.csv, clinical.csv, micro.csv (placeholder)"
APPLIED_FILTERS = "Brak filtrów (placeholder)"
ROW_COLUMN_COUNTS = "patient: 120×15, clinical: 340×12, micro: 890×18 (placeholder)"


class ReportMetadataPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        group = QGroupBox("Metadane raportu")
        group_layout = QVBoxLayout(group)

        group_layout.addWidget(QLabel(f"Tytuł sekcji: {SECTION_TITLE}"))
        group_layout.addWidget(QLabel(f"Dane źródłowe: {SOURCE_DATA}"))
        group_layout.addWidget(QLabel(f"Zastosowane filtry: {APPLIED_FILTERS}"))
        group_layout.addWidget(QLabel(f"Liczba wierszy i kolumn: {ROW_COLUMN_COUNTS}"))

        layout = QVBoxLayout(self)
        layout.addWidget(group)
