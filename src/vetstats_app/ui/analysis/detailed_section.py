from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

PLANNED_FEATURES = [
    "Definiowanie grup pacjentów",
    "Porównania między grupami",
    "Analiza niestandardowa z filtrami",
]


class DetailedAnalysisSection(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title_label = QLabel("Analiza szczegółowa")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        intro_label = QLabel(
            "Analiza zdefiniowana przez użytkownika: grupy pacjentów, porównania i niestandardowe zapytania."
        )
        intro_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_label.setWordWrap(True)

        features_group = QGroupBox("Planowane funkcje")
        features_layout = QVBoxLayout(features_group)
        for feature_name in PLANNED_FEATURES:
            features_layout.addWidget(QLabel(f"  • {feature_name}"))

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(intro_label)
        layout.addWidget(features_group)
        layout.addStretch()
