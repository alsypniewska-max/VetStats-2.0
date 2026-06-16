from __future__ import annotations

import io
from typing import Literal

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from vetstats_app.analysis.chart_models import AnalysisChartSpec

UI_CHART_WIDTH_INCHES = 6.0
UI_CHART_HEIGHT_INCHES = 3.6
UI_CHART_DPI = 100


def create_chart_widget(
    spec: AnalysisChartSpec,
    *,
    width_inches: float = UI_CHART_WIDTH_INCHES,
    height_inches: float = UI_CHART_HEIGHT_INCHES,
) -> QWidget:
    figure = _build_ui_figure(
        spec,
        width_inches=width_inches,
        height_inches=height_inches,
    )
    width_px = int(width_inches * UI_CHART_DPI)
    height_px = int(height_inches * UI_CHART_DPI)

    canvas = FigureCanvasQTAgg(figure)
    canvas.setFixedSize(width_px, height_px)

    container = QWidget()
    container.setFixedSize(width_px, height_px)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(
        canvas,
        alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
    )
    return container


def chart_spec_to_png_bytes(
    spec: AnalysisChartSpec,
    *,
    width_inches: float = 7.0,
    height_inches: float = 4.0,
    dpi: int = 120,
) -> bytes:
    figure = _build_figure(spec, width_inches=width_inches, height_inches=height_inches)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def _build_ui_figure(
    spec: AnalysisChartSpec,
    *,
    width_inches: float,
    height_inches: float,
) -> Figure:
    figure = Figure(figsize=(width_inches, height_inches), dpi=UI_CHART_DPI)
    axis = figure.add_subplot(111)
    _draw_chart(axis, spec, layout_mode="ui")
    figure.subplots_adjust(
        bottom=_ui_bottom_margin(spec),
        left=0.12,
        right=0.98,
        top=0.88,
    )
    return figure


def _build_figure(
    spec: AnalysisChartSpec,
    *,
    width_inches: float,
    height_inches: float,
) -> Figure:
    figure = Figure(figsize=(width_inches, height_inches), layout="constrained")
    axis = figure.add_subplot(111)
    _draw_chart(axis, spec, layout_mode="export")
    return figure


def _draw_chart(
    axis,
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> None:
    if spec.chart_type == "histogram":
        axis.hist(
            list(spec.values),
            bins=min(10, max(3, len(spec.values) // 2)),
            color="#4C78A8",
        )
    else:
        axis.bar(spec.labels, spec.values, color="#4C78A8")
        if layout_mode == "ui":
            _configure_ui_category_axis(axis, spec)
        else:
            axis.tick_params(axis="x", labelrotation=30)

    if layout_mode == "ui":
        axis.set_title(spec.title, fontsize=10)
    else:
        axis.set_title(spec.title)
    if spec.x_axis_label:
        axis.set_xlabel(spec.x_axis_label)
    if spec.y_axis_label:
        axis.set_ylabel(spec.y_axis_label)


def _configure_ui_category_axis(axis, spec: AnalysisChartSpec) -> None:
    if spec.chart_id == "microbiology_results" or _needs_rotated_labels(spec):
        axis.tick_params(axis="x", labelrotation=45, labelsize=8)
        for label in axis.get_xticklabels():
            label.set_ha("right")
        return

    axis.tick_params(axis="x", labelrotation=30, labelsize=9)
    for label in axis.get_xticklabels():
        label.set_ha("center")


def _needs_rotated_labels(spec: AnalysisChartSpec) -> bool:
    if len(spec.labels) > 6:
        return True
    return any(len(label) > 10 for label in spec.labels)


def _ui_bottom_margin(spec: AnalysisChartSpec) -> float:
    if spec.chart_id == "microbiology_results":
        return 0.42
    max_label_len = max((len(label) for label in spec.labels), default=0)
    if len(spec.labels) > 8 or max_label_len > 12:
        return 0.32
    if len(spec.labels) > 4:
        return 0.26
    return 0.20
