from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from vetstats_app.analysis.chart_models import AnalysisChartSpec


def create_chart_widget(
    spec: AnalysisChartSpec,
    *,
    width_inches: float = 6.0,
    height_inches: float = 3.6,
) -> QWidget:
    figure = _build_figure(spec, width_inches=width_inches, height_inches=height_inches)
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(FigureCanvasQTAgg(figure))
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


def _build_figure(
    spec: AnalysisChartSpec,
    *,
    width_inches: float,
    height_inches: float,
) -> Figure:
    figure = Figure(figsize=(width_inches, height_inches), layout="constrained")
    axis = figure.add_subplot(111)

    if spec.chart_type == "histogram":
        axis.hist(list(spec.values), bins=min(10, max(3, len(spec.values) // 2)), color="#4C78A8")
    else:
        axis.bar(spec.labels, spec.values, color="#4C78A8")
        axis.tick_params(axis="x", labelrotation=30)

    axis.set_title(spec.title)
    if spec.x_axis_label:
        axis.set_xlabel(spec.x_axis_label)
    if spec.y_axis_label:
        axis.set_ylabel(spec.y_axis_label)

    return figure
