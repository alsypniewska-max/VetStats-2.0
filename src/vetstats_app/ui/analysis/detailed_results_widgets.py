from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.detailed_comparative_analysis import (
    DetailedComparativeAnalysisResult,
)
from vetstats_app.ui.analysis.chart_widgets import build_chart_section
from vetstats_app.ui.analysis.interpretation_panel import build_wrapped_text_label
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
)


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _set_group_box_content(group_box: QGroupBox, widgets: list[QWidget]) -> None:
    layout = group_box.layout()
    assert layout is not None
    _clear_layout(layout)
    for widget in widgets:
        layout.addWidget(widget)


def populate_detailed_results(
    *,
    group_description_box: QGroupBox,
    descriptive_box: QGroupBox,
    statistical_box: QGroupBox,
    charts_box: QGroupBox,
    result: DetailedComparativeAnalysisResult,
) -> None:
    _set_group_box_content(
        group_description_box,
        [build_wrapped_text_label(result.group_description_text)],
    )

    descriptive_widgets: list[QWidget] = [
        build_wrapped_text_label(result.descriptive_summary_text),
    ]
    if result.categorical_rows:
        descriptive_widgets.append(
            _build_categorical_table(result, descriptive_box.window())
        )
    if result.numeric_rows:
        descriptive_widgets.append(_build_numeric_table(result))
    _set_group_box_content(descriptive_box, descriptive_widgets)

    statistical_widgets: list[QWidget] = [
        build_wrapped_text_label(result.statistical_summary_text),
        build_wrapped_text_label(result.interpretation_text),
    ]
    _set_group_box_content(statistical_box, statistical_widgets)

    chart_section = build_chart_section(
        "Wykres porównawczy",
        result.charts,
        empty_message="Brak wykresu dla wybranego porównania.",
    )
    _set_group_box_content(charts_box, [chart_section])


def _build_categorical_table(
    result: DetailedComparativeAnalysisResult,
    parent: QWidget | None,
) -> QTableWidget:
    table = QTableWidget(parent)
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(
        [
            "Kategoria",
            f"{result.group_1_name} (n)",
            f"{result.group_1_name} (%)",
            f"{result.group_2_name} (n)",
            f"{result.group_2_name} (%)",
        ]
    )
    table.setRowCount(len(result.categorical_rows))
    configure_reference_table(table)
    for row_index, row in enumerate(result.categorical_rows):
        table.setItem(row_index, 0, QTableWidgetItem(row.category))
        table.setItem(row_index, 1, QTableWidgetItem(str(row.group_1_count)))
        table.setItem(row_index, 2, QTableWidgetItem(f"{row.group_1_percent:.1f}"))
        table.setItem(row_index, 3, QTableWidgetItem(str(row.group_2_count)))
        table.setItem(row_index, 4, QTableWidgetItem(f"{row.group_2_percent:.1f}"))
    finalize_reference_table(table)
    return table


def _build_numeric_table(result: DetailedComparativeAnalysisResult) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(9)
    table.setHorizontalHeaderLabels(
        [
            "Grupa",
            "n",
            "Brakujące",
            "Średnia",
            "Mediana",
            "SD",
            "Min",
            "Max",
            "Q1–Q3",
        ]
    )
    table.setRowCount(len(result.numeric_rows))
    configure_reference_table(table)
    for row_index, row in enumerate(result.numeric_rows):
        q_text = (
            f"{row.percentile_25:.2f} – {row.percentile_75:.2f}"
            if row.percentile_25 is not None and row.percentile_75 is not None
            else "—"
        )
        table.setItem(row_index, 0, QTableWidgetItem(row.group_name))
        table.setItem(row_index, 1, QTableWidgetItem(str(row.n)))
        table.setItem(row_index, 2, QTableWidgetItem(str(row.missing)))
        table.setItem(row_index, 3, QTableWidgetItem(_fmt(row.mean)))
        table.setItem(row_index, 4, QTableWidgetItem(_fmt(row.median)))
        table.setItem(row_index, 5, QTableWidgetItem(_fmt(row.std)))
        table.setItem(row_index, 6, QTableWidgetItem(_fmt(row.minimum)))
        table.setItem(row_index, 7, QTableWidgetItem(_fmt(row.maximum)))
        table.setItem(row_index, 8, QTableWidgetItem(q_text))
    finalize_reference_table(table)
    return table


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"
