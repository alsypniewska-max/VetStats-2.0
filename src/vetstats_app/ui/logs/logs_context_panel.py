from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from vetstats_app.analysis.detailed_comparative_analysis import (
    format_detailed_analysis_settings_lines,
)
from vetstats_app.services.full_report_service import DetailedAnalysisContext


def _context_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class LogsContextPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._group = QGroupBox("Detailed Analysis — bieżąca konfiguracja")
        self._layout = QVBoxLayout(self._group)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._group)

        self._context_provider: Callable[[], DetailedAnalysisContext] | None = None
        self.show_placeholder()

    def set_context_provider(
        self,
        provider: Callable[[], DetailedAnalysisContext] | None,
    ) -> None:
        self._context_provider = provider

    def refresh(self) -> None:
        if self._context_provider is None:
            self.show_placeholder()
            return

        context = self._context_provider()
        lines = list(format_detailed_analysis_settings_lines(context.state))
        if context.last_result is not None and context.last_result.is_success:
            lines.append(
                "Ostatnia analiza: zakończona pomyślnie "
                f"({context.last_result.variable_label})."
            )
        elif context.last_result is not None:
            lines.append("Ostatnia analiza: nie powiodła się.")
        self._set_lines(tuple(lines))

    def show_placeholder(self) -> None:
        self._set_lines(("Brak podłączonego kontekstu Detailed Analysis.",))

    def _set_lines(self, lines: tuple[str, ...]) -> None:
        self._clear_content()
        for line in lines:
            self._layout.addWidget(_context_label(line))

    def _clear_content(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
