from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

HISTORY_SECTIONS = [
    ("Historia wizyt", "Placeholder: lista wizyt pacjenta."),
    ("Diagnozy", "Placeholder: historia diagnoz."),
    ("Leczenie", "Placeholder: zastosowane leczenie."),
    ("Mikrobiologia", "Placeholder: wyniki badań mikrobiologicznych."),
]


class PatientDetailsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        header = QLabel(
            "Pacjent: Burek  |  ID: 001  |  Gatunek: pies  |  Rasa: xxx  |  Wiek: xxx"
        )
        header.setWordWrap(True)

        xxx_note = QLabel(
            'Pola o wartości "xxx" będą później wyświetlane jako "nie wiadomo".'
        )
        xxx_note.setWordWrap(True)

        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        for title, placeholder_text in HISTORY_SECTIONS:
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            group_layout.addWidget(QLabel(placeholder_text))
            sections_layout.addWidget(group)
        sections_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(sections_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(header)
        layout.addWidget(xxx_note)
        layout.addWidget(scroll_area)
