from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
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
    extra_height_inches = _legend_extra_height_inches(spec)
    figure = _build_ui_figure(
        spec,
        width_inches=width_inches,
        height_inches=height_inches + extra_height_inches,
    )
    total_height_inches = height_inches + extra_height_inches
    width_px = int(width_inches * UI_CHART_DPI)
    height_px = int(total_height_inches * UI_CHART_DPI)

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
    extra_height_inches = _legend_extra_height_inches(spec)
    figure = _build_figure(
        spec,
        width_inches=width_inches,
        height_inches=height_inches + extra_height_inches,
    )
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def save_chart_spec(
    spec: AnalysisChartSpec,
    destination: Path,
    *,
    file_format: str,
    dpi: int,
    width_inches: float = 7.0,
    height_inches: float = 4.0,
) -> None:
    extra_height_inches = _legend_extra_height_inches(spec)
    figure = _build_figure(
        spec,
        width_inches=width_inches,
        height_inches=height_inches + extra_height_inches,
    )
    try:
        figure.savefig(destination, format=file_format, dpi=dpi, bbox_inches="tight")
    finally:
        plt.close(figure)


def save_chart_specs_to_pdf(
    specs: tuple[AnalysisChartSpec, ...],
    destination: Path,
    *,
    dpi: int,
    width_inches: float = 7.0,
    height_inches: float = 4.0,
) -> None:
    with PdfPages(destination) as pdf:
        for spec in specs:
            extra_height_inches = _legend_extra_height_inches(spec)
            figure = _build_figure(
                spec,
                width_inches=width_inches,
                height_inches=height_inches + extra_height_inches,
            )
            try:
                pdf.savefig(figure, dpi=dpi, bbox_inches="tight")
            finally:
                plt.close(figure)


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
        left=_ui_left_margin(spec),
        right=0.98,
        top=0.88,
    )
    _attach_legend_note(figure, spec, layout_mode="ui")
    return figure


def _build_figure(
    spec: AnalysisChartSpec,
    *,
    width_inches: float,
    height_inches: float,
) -> Figure:
    figure = Figure(figsize=(width_inches, height_inches))
    axis = figure.add_subplot(111)
    _draw_chart(axis, spec, layout_mode="export")
    if spec.legend_note.strip():
        figure.subplots_adjust(
            bottom=_export_bottom_margin(spec),
            left=_ui_left_margin(spec),
            right=0.98,
            top=0.88,
        )
        _attach_legend_note(figure, spec, layout_mode="export")
    else:
        figure.set_layout_engine("constrained")
    return figure


def _legend_line_count(spec: AnalysisChartSpec) -> int:
    if not spec.legend_note.strip():
        return 0
    return spec.legend_note.count("\n") + 1


def _legend_extra_height_inches(spec: AnalysisChartSpec) -> float:
    line_count = _legend_line_count(spec)
    if line_count == 0:
        return 0.0
    return min(1.4, 0.22 + line_count * 0.11)


def _legend_bottom_fraction(spec: AnalysisChartSpec) -> float:
    line_count = _legend_line_count(spec)
    if line_count == 0:
        return 0.0
    return min(0.42, 0.06 + line_count * 0.035)


def _attach_legend_note(
    figure: Figure,
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> None:
    if not spec.legend_note.strip():
        return

    fontsize = 7 if layout_mode == "ui" else 8
    figure.text(
        0.02,
        0.01,
        spec.legend_note,
        ha="left",
        va="bottom",
        fontsize=fontsize,
        transform=figure.transFigure,
    )


def _export_bottom_margin(spec: AnalysisChartSpec) -> float:
    base = 0.14 if spec.orientation == "horizontal" else 0.20
    return base + _legend_bottom_fraction(spec)


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
    elif spec.orientation == "horizontal":
        y_positions = range(len(spec.labels))
        axis.barh(list(y_positions), spec.values, color="#4C78A8")
        axis.set_yticks(list(y_positions))
        label_size = 8 if layout_mode == "ui" else 9
        axis.set_yticklabels(spec.labels, fontsize=label_size)
        axis.invert_yaxis()
        if layout_mode == "ui":
            axis.tick_params(axis="y", labelsize=label_size)
        else:
            axis.tick_params(axis="y", labelsize=label_size)
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
    if spec.orientation == "horizontal":
        if spec.y_axis_label:
            axis.set_xlabel(spec.y_axis_label)
        if spec.x_axis_label:
            axis.set_ylabel(spec.x_axis_label)
    else:
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


def _ui_left_margin(spec: AnalysisChartSpec) -> float:
    if spec.orientation != "horizontal":
        return 0.12

    max_label_len = max((len(label) for label in spec.labels), default=0)
    if max_label_len > 35:
        return 0.50
    if max_label_len > 25:
        return 0.42
    if max_label_len > 15:
        return 0.34
    return 0.28


def _ui_bottom_margin(spec: AnalysisChartSpec) -> float:
    if spec.orientation == "horizontal":
        base = 0.14
    elif spec.chart_id == "microbiology_results":
        base = 0.42
    else:
        max_label_len = max((len(label) for label in spec.labels), default=0)
        if len(spec.labels) > 8 or max_label_len > 12:
            base = 0.32
        elif len(spec.labels) > 4:
            base = 0.26
        else:
            base = 0.20
    return base + _legend_bottom_fraction(spec)
