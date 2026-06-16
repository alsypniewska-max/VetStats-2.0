from PyQt6.QtWidgets import QPushButton

_COMPACT_BUTTON_STYLE = (
    "QPushButton {"
    "  padding: 3px 10px;"
    "  min-height: 22px;"
    "  max-height: 26px;"
    "}"
)


def apply_compact_analysis_button_style(button: QPushButton) -> None:
    button.setStyleSheet(_COMPACT_BUTTON_STYLE)
