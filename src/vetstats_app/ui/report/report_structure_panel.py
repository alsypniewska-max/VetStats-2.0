from PyQt6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

REPORT_SECTIONS = [
    (
        "Wyniki opisowe",
        "Placeholder: opisowe podsumowanie wyników analizy.",
    ),
    (
        "Tabele podsumowujące",
        "Placeholder: tabele podsumowujące dane weterynaryjne i antybiogram.",
    ),
    (
        "Wykresy",
        (
            "Placeholder: wykresy wyników analizy. "
            "Wykresy przeznaczone do układu poziomego; "
            "tekst i tabele przeznaczone do układu pionowego A4."
        ),
    ),
]


class ReportStructurePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        for title, placeholder_text in REPORT_SECTIONS:
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            label = QLabel(placeholder_text)
            label.setWordWrap(True)
            group_layout.addWidget(label)
            sections_layout.addWidget(group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(sections_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)
