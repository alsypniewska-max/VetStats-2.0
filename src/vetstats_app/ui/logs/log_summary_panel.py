from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget


class LogSummaryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        group = QGroupBox("Informacje o logu sesji")
        group_layout = QVBoxLayout(group)

        group_layout.addWidget(
            QLabel(
                "Ta zakładka będzie wyświetlać pełny log bieżącej sesji aplikacji."
            )
        )
        group_layout.addWidget(
            QLabel(
                "Każdy wpis logu zawiera: datę, godzinę, typ logu oraz treść wiadomości."
            )
        )

        layout = QVBoxLayout(self)
        layout.addWidget(group)
