from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.chart_specs import build_ems_treatment_duration_charts
from vetstats_app.analysis.ems_treatment_duration import (
    MIN_DISPLAY_GROUP_SIZE,
    EmsTreatmentDurationResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
    cat_overall_comparison_table_block,
    cat_ulcer_comparison_table_block,
    dog_breed_comparison_table_block,
    dog_overall_comparison_table_block,
    dog_ulcer_comparison_table_block,
    exclusions_table_block,
    overall_comparison_table_block,
    statistical_tests_table_block,
    ulcer_comparison_table_block,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.ems_treatment_duration_service import EmsTreatmentDurationService
from vetstats_app.ui.analysis.chart_export_dialog import open_chart_export_dialog
from vetstats_app.ui.analysis.chart_widgets import build_chart_section
from vetstats_app.ui.analysis.interpretation_panel import (
    build_interpretation_section,
    build_wrapped_text_label,
)
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
)


def _configure_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_table(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for column_index in range(table.columnCount()):
        header.setSectionResizeMode(
            column_index,
            QHeaderView.ResizeMode.ResizeToContents,
        )
    finalize_reference_table(table)
    total_width = table.frameWidth() * 2
    if table.verticalHeader().isVisible():
        total_width += table.verticalHeader().width()
    for column_index in range(table.columnCount()):
        total_width += table.columnWidth(column_index)
    table.setMaximumWidth(total_width)


def _table_from_block(block) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_table(table)
    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
    _finalize_table(table)
    return table


def _add_table_group(
    content_layout: QVBoxLayout,
    block,
    *,
    note: str | None = None,
    empty_note: str | None = None,
) -> None:
    if not block.rows and empty_note is None:
        return
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)
    if note:
        layout.addWidget(build_wrapped_text_label(note))
    if block.rows:
        layout.addWidget(_table_from_block(block))
    elif empty_note:
        layout.addWidget(build_wrapped_text_label(empty_note))
    content_layout.addWidget(group)


def _sparse_group_note(layer_label: str) -> str:
    return (
        f"Brak grup EMS do wyświetlenia ({layer_label}): żadna grupa EMS tak ani EMS nie "
        f"nie osiągnęła progu n≥{MIN_DISPLAY_GROUP_SIZE}."
    )


class EmsTreatmentDurationView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = EmsTreatmentDurationService().analyze()
        self._report_service = AnalysisReportService()
        result = self._result

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")
        self._action_bar_widget = build_module_action_bar(
            generate_report_button,
            export_charts_button,
        )
        generate_report_button.clicked.connect(self._on_generate_report)
        export_charts_button.clicked.connect(self._on_export_charts)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            build_wrapped_text_label(
                "Moduł analizuje czas leczenia uleczonych przypadków wrzodowych "
                "leczonych farmakologicznie (farmacology_surgery = f) i porównuje "
                "przypadki z EMS (tak) oraz bez EMS (nie). EMS odczytywany jest z "
                "wiersza kończącego leczenie."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        stats_block = build_descriptive_stats_block(result)
        stats_group = QGroupBox(stats_block.title)
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.addWidget(_table_from_block(stats_block))
        content_layout.addWidget(stats_group)

        exclusions_block = exclusions_table_block(result)
        exclusions_group = QGroupBox(exclusions_block.title)
        exclusions_layout = QVBoxLayout(exclusions_group)
        exclusions_layout.addWidget(_table_from_block(exclusions_block))
        content_layout.addWidget(exclusions_group)

        _add_table_group(
            content_layout,
            overall_comparison_table_block(result),
            empty_note=_sparse_group_note("łącznie"),
        )
        _add_table_group(
            content_layout,
            ulcer_comparison_table_block(result),
            note=(
                f"Uwaga: w tabelach pokazywane są grupy EMS z co najmniej "
                f"{MIN_DISPLAY_GROUP_SIZE} przypadkami; wiersz typu wrzodu pojawia się, "
                f"gdy co najmniej jedna grupa EMS spełnia ten próg."
            ),
            empty_note=_sparse_group_note("według typu wrzodu — łącznie"),
        )
        _add_table_group(
            content_layout,
            dog_overall_comparison_table_block(result),
            note=(
                "Analiza gatunkowa obejmuje wyłącznie psy ze znaną klasyfikacją gatunku."
            ),
            empty_note=_sparse_group_note("psy — łącznie"),
        )
        _add_table_group(
            content_layout,
            dog_ulcer_comparison_table_block(result),
            empty_note=_sparse_group_note("psy — według typu wrzodu"),
        )
        _add_table_group(
            content_layout,
            cat_overall_comparison_table_block(result),
            note=(
                "Analiza gatunkowa obejmuje wyłącznie koty ze znaną klasyfikacją gatunku."
            ),
            empty_note=_sparse_group_note("koty — łącznie"),
        )
        _add_table_group(
            content_layout,
            cat_ulcer_comparison_table_block(result),
            empty_note=_sparse_group_note("koty — według typu wrzodu"),
        )
        _add_table_group(
            content_layout,
            dog_breed_comparison_table_block(result),
            note=(
                f"Warstwa rasowa (psy): rasa pojawia się w tabeli, gdy co najmniej jedna "
                f"grupa EMS (tak lub nie) ma n≥{MIN_DISPLAY_GROUP_SIZE}; wykres rasowy "
                f"wymaga obu grup EMS z n≥{MIN_DISPLAY_GROUP_SIZE}."
            ),
            empty_note=(
                f"Brak ras do wyświetlenia: żadna rasa nie ma grupy EMS tak ani EMS nie "
                f"z n≥{MIN_DISPLAY_GROUP_SIZE}."
            ),
        )

        if result.statistical_tests:
            tests_block = statistical_tests_table_block(result)
            tests_group = QGroupBox(tests_block.title)
            tests_layout = QVBoxLayout(tests_group)
            tests_layout.addWidget(
                build_wrapped_text_label(
                    "Porównania per typ wrzodu zawierają skorygowane p-value (Benjamini–"
                    "Hochberg) w obrębie każdej warstwy. Wyniki opisują skojarzenie, "
                    "nie przyczynowość."
                )
            )
            tests_layout.addWidget(_table_from_block(tests_block))
            content_layout.addWidget(tests_group)

        chart_group = build_chart_section(
            "Wykresy",
            build_ems_treatment_duration_charts(result),
            empty_message="Brak danych do wygenerowania wykresów.",
        )
        content_layout.addWidget(chart_group)
        content_layout.addWidget(
            build_interpretation_section(build_interpretation_summary(result))
        )

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area, stretch=1)

    def action_bar_widget(self) -> QWidget:
        return self._action_bar_widget

    def _on_generate_report(self) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Generuj raport",
            "ems_treatment_duration_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return
        error_message = self._report_service.export_ems_treatment_duration_report_pdf(
            self._result,
            Path(destination),
        )
        if error_message is not None:
            QMessageBox.warning(self, "Generuj raport", error_message)
            return
        QMessageBox.information(
            self,
            "Generuj raport",
            f"Zapisano raport PDF do pliku:\n{destination}",
        )

    def _on_export_charts(self) -> None:
        open_chart_export_dialog(
            self,
            build_ems_treatment_duration_charts(self._result),
        )
