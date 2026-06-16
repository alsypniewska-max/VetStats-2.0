from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from vetstats_app.ui.analysis.analysis_button_style import apply_compact_analysis_button_style


def build_module_action_bar(*buttons: QPushButton) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    for button in buttons:
        apply_compact_analysis_button_style(button)
        layout.addWidget(button)
    return widget