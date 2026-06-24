from PyQt6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

REPORT_SECTIONS = [
    (
        "Strona tytułowa",
        "Logo VetStats, nazwa aplikacji, tytuł „Raport analizy”, data wygenerowania "
        "oraz informacja o źródle danych.",
    ),
    (
        "Podsumowanie raportu",
        "Opis źródeł danych, filtrów, wymiarów zbiorów, skrót interpretacji oraz "
        "przegląd sekcji analizy automatycznej.",
    ),
    (
        "Analiza automatyczna (15 modułów)",
        "Po kolei wszystkie moduły z zakładki Analysis: charakterystyka populacji, "
        "częstość rozpoznań, leczenie, mikrobiologia, oporność, powiązania kliniczne, "
        "czas leczenia, EMS, czas problemu, rozkład wymazów, leki przed wymazem "
        "oraz powiązania patient_ID — każdy z tabelami i wykresami.",
    ),
    (
        "Analiza szczegółowa",
        "Bieżąca konfiguracja porównania grup z zakładki Analysis (opis grup, "
        "statystyka opisowa, testy statystyczne i wykresy).",
    ),
    (
        "Podsumowanie końcowe",
        "Krótkie zamknięcie raportu z informacją o zakresie dołączonych sekcji.",
    ),
]


class ReportStructurePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        for title, description in REPORT_SECTIONS:
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            label = QLabel(description)
            label.setWordWrap(True)
            group_layout.addWidget(label)
            sections_layout.addWidget(group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(sections_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)
