from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.services.analysis_chart_renderer import create_chart_widget


def exportable_charts(
    charts: tuple[AnalysisChartSpec, ...],
) -> tuple[AnalysisChartSpec, ...]:
    return tuple(chart for chart in charts if chart.has_data)


def build_chart_section(
    title: str,
    charts: tuple[AnalysisChartSpec, ...],
    *,
    empty_message: str = "Brak danych do wygenerowania wykresu.",
) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)

    if not charts:
        layout.addWidget(QLabel(empty_message))
        return group

    for chart in exportable_charts(charts):
        layout.addWidget(
            create_chart_widget(chart),
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )

    if layout.count() == 0:
        layout.addWidget(QLabel(empty_message))

    return group
