from collections.abc import Callable

from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from vetstats_app.ui.analysis.analysis_button_style import apply_compact_analysis_button_style
SECTION_LABELS = [
    "Analiza automatyczna",
    "Analiza szczegółowa",
]


class SectionSwitchBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for index, label in enumerate(SECTION_LABELS):
            button = QPushButton(label)
            button.setCheckable(True)
            apply_compact_analysis_button_style(button)
            self._button_group.addButton(button, index)
            layout.addWidget(button)

        self.set_current_section(0)

    def connect_section_changed(self, callback: Callable[[int], None]) -> None:
        self._button_group.idClicked.connect(callback)

    def set_current_section(self, index: int) -> None:
        button = self._button_group.button(index)
        if button is not None:
            button.setChecked(True)
