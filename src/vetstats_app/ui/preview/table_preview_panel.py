from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TablePreviewPanel(QWidget):
    def __init__(self, table_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title_label = QLabel(table_name)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description_label = QLabel(f"Placeholder: podgląd tabeli {table_name}.")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()
