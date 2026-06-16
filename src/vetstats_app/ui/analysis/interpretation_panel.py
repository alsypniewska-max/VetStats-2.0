from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QSizePolicy, QVBoxLayout


def build_wrapped_text_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
    return label


def build_interpretation_section(text: str) -> QGroupBox:
    group = QGroupBox("Interpretacja")
    layout = QVBoxLayout(group)
    layout.addWidget(build_wrapped_text_label(text))
    return group
