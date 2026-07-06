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

from vetstats_app.analysis.breed_treatment_duration import (
    BreedTreatmentDurationResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
    cat_breeds_table_block,
    dog_breeds_table_block,
    exclusions_table_block,
    species_summary_table_block,
    statistical_tests_table_block,
)
from vetstats_app.analysis.chart_specs import build_breed_treatment_duration_charts
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.breed_treatment_duration_service import (
    BreedTreatmentDurationService,
)
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

MODULE_TITLE = "Rasa a czas leczenia"


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


class BreedTreatmentDurationView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = BreedTreatmentDurationService().analyze()
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
                "Moduł analizuje czas leczenia wyleczonych przypadków wrzodowych "
                "według gatunku i rasy, osobno dla psów i kotów."
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

        if result.dog_summary or result.cat_summary:
            species_block = species_summary_table_block(result)
            species_group = QGroupBox(species_block.title)
            species_layout = QVBoxLayout(species_group)
            species_layout.addWidget(
                build_wrapped_text_label(
                    "Uwaga: podsumowanie gatunkowe obejmuje przypadki bez znanej rasy; "
                    "tabele rasowe poniżej — wyłącznie ze znaną rasą."
                )
            )
            species_layout.addWidget(_table_from_block(species_block))
            content_layout.addWidget(species_group)

        if result.dog_breeds:
            dog_block = dog_breeds_table_block(result)
            dog_group = QGroupBox(dog_block.title)
            dog_layout = QVBoxLayout(dog_group)
            dog_layout.addWidget(_table_from_block(dog_block))
            content_layout.addWidget(dog_group)

        if result.cat_breeds:
            cat_block = cat_breeds_table_block(result)
            cat_group = QGroupBox(cat_block.title)
            cat_layout = QVBoxLayout(cat_group)
            cat_layout.addWidget(_table_from_block(cat_block))
            content_layout.addWidget(cat_group)

        if result.statistical_tests:
            tests_block = statistical_tests_table_block(result)
            tests_group = QGroupBox(tests_block.title)
            tests_layout = QVBoxLayout(tests_group)
            tests_layout.addWidget(_table_from_block(tests_block))
            content_layout.addWidget(tests_group)

        chart_group = build_chart_section(
            "Wykresy",
            build_breed_treatment_duration_charts(result),
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
            "breed_treatment_duration_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return
        error_message = self._report_service.export_breed_treatment_duration_report_pdf(
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
            build_breed_treatment_duration_charts(self._result),
        )
