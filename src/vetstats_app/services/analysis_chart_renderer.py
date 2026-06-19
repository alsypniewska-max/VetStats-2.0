from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
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
        top=_figure_top_margin(spec, layout_mode="ui"),
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
    if spec.legend_note.strip() or _pre_swab_chart(spec):
        figure.subplots_adjust(
            bottom=_export_bottom_margin(spec),
            left=_ui_left_margin(spec),
            right=0.98,
            top=_figure_top_margin(spec, layout_mode="export"),
        )
        if spec.legend_note.strip():
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
    base = 0.14 if spec.orientation == "horizontal" else _category_axis_bottom_margin(spec)
    return base + _legend_bottom_fraction(spec)


def _duration_problem_histogram_bins(values: tuple[float, ...]) -> list[float]:
    max_value = max(values)
    edges = [0.0, 7.0, 14.0, 30.0, 60.0, 90.0, 180.0, 365.0]
    if max_value > edges[-1]:
        edges.append(float(max_value) + 1.0)
    else:
        while len(edges) > 4 and edges[-1] > max_value:
            edges.pop()
        if edges[-1] <= max_value:
            edges.append(float(max_value) + 1.0)
    return edges


def _chart_title(spec: AnalysisChartSpec, *, layout_mode: str) -> str:
    return _formatted_chart_title(spec, layout_mode=layout_mode)


_MEASURE_FIGURE: Figure | None = None
_MEASURE_RENDERER = None


def _get_measure_renderer():
    global _MEASURE_FIGURE, _MEASURE_RENDERER
    if _MEASURE_RENDERER is None:
        _MEASURE_FIGURE = Figure(figsize=(1, 1))
        canvas = FigureCanvasAgg(_MEASURE_FIGURE)
        _MEASURE_RENDERER = canvas.get_renderer()
    return _MEASURE_RENDERER


def _chart_width_inches(layout_mode: Literal["ui", "export"]) -> float:
    return UI_CHART_WIDTH_INCHES if layout_mode == "ui" else 7.0


def _title_fontproperties(layout_mode: Literal["ui", "export"]):
    from matplotlib.font_manager import FontProperties

    if layout_mode == "ui":
        return FontProperties(size=10)
    return FontProperties(size=plt.rcParams.get("axes.titlesize", 10))


def _text_width_points(text: str, *, layout_mode: Literal["ui", "export"]) -> float:
    renderer = _get_measure_renderer()
    width, _, _ = renderer.get_text_width_height_descent(
        text,
        _title_fontproperties(layout_mode),
        ismath=False,
    )
    return width


def _title_max_width_points(
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> float:
    width_inches = _chart_width_inches(layout_mode)
    available_inches = (0.98 - _ui_left_margin(spec)) * width_inches
    return available_inches * 72.0 * 0.96


def _wrap_text_to_width(
    text: str,
    *,
    max_width_points: float,
    layout_mode: Literal["ui", "export"],
) -> str:
    words = text.split()
    if not words:
        return text

    if len(words) == 1:
        if _text_width_points(text, layout_mode=layout_mode) <= max_width_points:
            return text
        break_at = max(1, len(text) // 2)
        return f"{text[:break_at]}\n{text[break_at:]}"

    lines: list[str] = []
    current_words: list[str] = []
    for word in words:
        candidate = " ".join(current_words + [word])
        if (
            current_words
            and _text_width_points(candidate, layout_mode=layout_mode) > max_width_points
        ):
            lines.append(" ".join(current_words))
            current_words = [word]
        else:
            current_words.append(word)
    if current_words:
        lines.append(" ".join(current_words))
    return "\n".join(lines)


def _formatted_width_aware_chart_title(
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> str:
    max_width_points = _title_max_width_points(spec, layout_mode=layout_mode)
    title = _wrap_text_to_width(
        spec.title,
        max_width_points=max_width_points,
        layout_mode=layout_mode,
    )
    if spec.subtitle.strip():
        subtitle = _wrap_text_to_width(
            spec.subtitle,
            max_width_points=max_width_points,
            layout_mode=layout_mode,
        )
        return f"{title}\n{subtitle}"
    return title


def _title_wrap_max_line_length(
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> int:
    return 34 if layout_mode == "ui" else 42


def _formatted_chart_title(
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> str:
    if spec.chart_id == "pre_swab_treatment_status_culture":
        return _formatted_width_aware_chart_title(spec, layout_mode=layout_mode)

    max_line_length = _title_wrap_max_line_length(spec, layout_mode=layout_mode)
    title = _wrap_label_text(spec.title, max_line_length=max_line_length)
    if spec.subtitle.strip():
        subtitle = _wrap_label_text(spec.subtitle, max_line_length=max_line_length)
        return f"{title}\n{subtitle}"
    return title


def _chart_title_line_count(
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> int:
    return _formatted_chart_title(spec, layout_mode=layout_mode).count("\n") + 1


def _figure_top_margin(
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> float:
    line_count = _chart_title_line_count(spec, layout_mode=layout_mode)
    margins = {
        1: 0.90,
        2: 0.87,
        3: 0.83,
        4: 0.79,
        5: 0.75,
        6: 0.72,
    }
    return margins.get(line_count, max(0.68, 0.90 - (line_count - 1) * 0.04))


def _pre_swab_chart(spec: AnalysisChartSpec) -> bool:
    return spec.chart_id.startswith("pre_swab_")


def _wrap_label_text(label: str, *, max_line_length: int = 18) -> str:
    if len(label) <= max_line_length:
        return label

    words = label.split()
    if len(words) <= 1:
        break_at = max(1, len(label) // 2)
        return f"{label[:break_at]}\n{label[break_at:]}"

    lines: list[str] = []
    current_words: list[str] = []
    current_length = 0
    for word in words:
        extra = len(word) + (1 if current_words else 0)
        if current_words and current_length + extra > max_line_length:
            lines.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
        else:
            current_words.append(word)
            current_length += extra
    if current_words:
        lines.append(" ".join(current_words))
    return "\n".join(lines)


def _display_category_labels(spec: AnalysisChartSpec) -> tuple[str, ...]:
    if not _pre_swab_chart(spec):
        return spec.labels

    if spec.chart_id in {
        "pre_swab_culture_outcomes",
        "pre_swab_top_drug_culture",
        "pre_swab_no_prior_culture",
        "pre_swab_treatment_buckets",
        "pre_swab_treatment_status_culture",
    }:
        max_line_length = 14
    else:
        max_line_length = 16

    return tuple(
        _wrap_label_text(label, max_line_length=max_line_length) for label in spec.labels
    )


def _category_labels_are_multiline(spec: AnalysisChartSpec) -> bool:
    return any("\n" in label for label in _display_category_labels(spec))


def _category_label_rotation(spec: AnalysisChartSpec) -> int:
    if _pre_swab_chart(spec):
        if _category_labels_are_multiline(spec):
            return 0
        if any(len(label) > 12 for label in spec.labels):
            return 45
        return 30
    if spec.chart_id == "microbiology_results" or _needs_rotated_labels(spec):
        return 45
    return 30


def _draw_vertical_bar_chart(
    axis,
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> None:
    display_labels = _display_category_labels(spec)
    if _pre_swab_chart(spec):
        positions = list(range(len(spec.labels)))
        axis.bar(positions, spec.values, color="#4C78A8")
        axis.set_xticks(positions)
        label_size = 8 if layout_mode == "ui" else 9
        axis.set_xticklabels(display_labels, fontsize=label_size)
    else:
        axis.bar(spec.labels, spec.values, color="#4C78A8")

    _configure_category_axis(axis, spec, layout_mode=layout_mode)


def _configure_category_axis(
    axis,
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> None:
    rotation = _category_label_rotation(spec)
    label_size = 8 if layout_mode == "ui" else 9
    tick_pad = 2 if spec.chart_id == "pre_swab_top_drugs" else 4
    axis.tick_params(
        axis="x",
        labelrotation=rotation,
        labelsize=label_size,
        pad=tick_pad,
    )
    horizontal_alignment = "right" if rotation >= 45 else "center"
    for label in axis.get_xticklabels():
        label.set_ha(horizontal_alignment)


def _apply_x_axis_label(axis, spec: AnalysisChartSpec) -> None:
    if not spec.x_axis_label:
        return
    if spec.chart_id == "pre_swab_top_drugs":
        axis.set_xlabel(spec.x_axis_label)
        axis.xaxis.set_label_coords(0.5, -0.15)
        return
    axis.set_xlabel(spec.x_axis_label, labelpad=4)


def _category_axis_bottom_margin(spec: AnalysisChartSpec) -> float:
    if spec.orientation == "horizontal":
        return 0.14

    if spec.chart_id == "microbiology_results":
        return 0.42

    if _pre_swab_chart(spec):
        line_count = max(
            (label.count("\n") + 1 for label in _display_category_labels(spec)),
            default=1,
        )
        base = 0.20 + (line_count - 1) * 0.07
        if _category_label_rotation(spec) >= 45:
            base = max(base, 0.36)
        elif _category_labels_are_multiline(spec):
            base = max(base, 0.30)
        return base

    max_label_len = max((len(label) for label in spec.labels), default=0)
    if len(spec.labels) > 8 or max_label_len > 12:
        return 0.32
    if len(spec.labels) > 4:
        return 0.26
    return 0.20


def _draw_chart(
    axis,
    spec: AnalysisChartSpec,
    *,
    layout_mode: Literal["ui", "export"],
) -> None:
    if spec.chart_type == "histogram":
        values = list(spec.values)
        if spec.chart_id == "duration_of_problem_histogram":
            bins = _duration_problem_histogram_bins(spec.values)
        else:
            bins = min(10, max(3, len(values) // 2))
        axis.hist(values, bins=bins, color="#4C78A8")
    elif spec.chart_type == "grouped_bar":
        positions = list(range(len(spec.labels)))
        bar_width = 0.38
        axis.bar(
            [position - bar_width / 2 for position in positions],
            spec.values,
            width=bar_width,
            label="Średnia",
            color="#4C78A8",
        )
        axis.bar(
            [position + bar_width / 2 for position in positions],
            spec.secondary_values,
            width=bar_width,
            label="Mediana",
            color="#F58518",
        )
        axis.set_xticks(positions)
        label_size = 8 if layout_mode == "ui" else 9
        axis.set_xticklabels(spec.labels, fontsize=label_size)
        axis.legend(fontsize=7 if layout_mode == "ui" else 8)
        _configure_category_axis(axis, spec, layout_mode=layout_mode)
    elif spec.chart_type == "stacked_bar":
        display_labels = _display_category_labels(spec)
        positions = list(range(len(spec.labels)))
        bottoms = [0.0] * len(spec.labels)
        colors = ("#4C78A8", "#F58518", "#54A24B", "#B279A2")
        for series_index, series_values in enumerate(spec.stacked_series_values):
            axis.bar(
                positions,
                series_values,
                bottom=bottoms,
                width=0.65,
                label=spec.stacked_series_labels[series_index],
                color=colors[series_index % len(colors)],
            )
            bottoms = [bottom + value for bottom, value in zip(bottoms, series_values)]
        axis.set_xticks(positions)
        label_size = 8 if layout_mode == "ui" else 9
        axis.set_xticklabels(display_labels, fontsize=label_size)
        axis.legend(fontsize=7 if layout_mode == "ui" else 8)
        _configure_category_axis(axis, spec, layout_mode=layout_mode)
    elif spec.chart_type == "box":
        axis.boxplot(
            [list(group) for group in spec.box_plot_groups],
            tick_labels=list(spec.labels),
            showfliers=True,
            patch_artist=True,
            boxprops={"facecolor": "#4C78A8", "alpha": 0.65},
            medianprops={"color": "#1F1F1F"},
        )
        if layout_mode == "ui":
            _configure_category_axis(axis, spec, layout_mode=layout_mode)
        else:
            _configure_category_axis(axis, spec, layout_mode=layout_mode)
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
        _draw_vertical_bar_chart(axis, spec, layout_mode=layout_mode)

    if layout_mode == "ui":
        axis.set_title(
            _chart_title(spec, layout_mode=layout_mode),
            fontsize=10,
            pad=6,
        )
    else:
        axis.set_title(_chart_title(spec, layout_mode=layout_mode), pad=8)
    if spec.orientation == "horizontal":
        if spec.y_axis_label:
            axis.set_xlabel(spec.y_axis_label)
        if spec.x_axis_label:
            axis.set_ylabel(spec.x_axis_label)
    else:
        _apply_x_axis_label(axis, spec)
        if spec.y_axis_label:
            axis.set_ylabel(spec.y_axis_label)


def _ui_bottom_margin(spec: AnalysisChartSpec) -> float:
    return _category_axis_bottom_margin(spec) + _legend_bottom_fraction(spec)


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
