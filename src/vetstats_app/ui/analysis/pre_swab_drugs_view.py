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

from vetstats_app.analysis.chart_specs import build_pre_swab_drugs_charts
from vetstats_app.analysis.pre_swab_drugs import (
    PreSwabDrugsResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
    culture_outcomes_table_block,
    drug_culture_crosstab_table_block,
    top_drugs_table_block,
    treatment_status_culture_crosstab_table_block,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.pre_swab_drugs_service import PreSwabDrugsService
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

MODULE_TITLE = "Leki stosowane przed wymazem"


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


class PreSwabDrugsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = PreSwabDrugsService().analyze()
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
                "Moduł analizuje pole drug_used_before_micro w tabeli clinical "
                "oraz porównuje leki stosowane przed wymazem z wynikami posiewu "
                "po dopasowaniu clinical–micro."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        stats_block = build_descriptive_stats_block(result)
        stats_group = QGroupBox(stats_block.title)
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.addWidget(_table_from_block(stats_block))
        content_layout.addWidget(stats_group)

        if result.top_drugs:
            top_block = top_drugs_table_block(result)
            top_group = QGroupBox(top_block.title)
            top_layout = QVBoxLayout(top_group)
            top_layout.addWidget(_table_from_block(top_block))
            content_layout.addWidget(top_group)

        if result.culture_outcomes:
            culture_block = culture_outcomes_table_block(result)
            culture_group = QGroupBox(culture_block.title)
            culture_layout = QVBoxLayout(culture_group)
            culture_layout.addWidget(_table_from_block(culture_block))
            content_layout.addWidget(culture_group)

        if result.treatment_status_culture_crosstab:
            status_block = treatment_status_culture_crosstab_table_block(result)
            status_group = QGroupBox(status_block.title)
            status_layout = QVBoxLayout(status_group)
            status_layout.addWidget(_table_from_block(status_block))
            content_layout.addWidget(status_group)

        if result.drug_culture_crosstab:
            cross_block = drug_culture_crosstab_table_block(result)
            cross_group = QGroupBox(cross_block.title)
            cross_layout = QVBoxLayout(cross_group)
            cross_layout.addWidget(_table_from_block(cross_block))
            content_layout.addWidget(cross_group)

        chart_group = build_chart_section(
            "Wykresy",
            build_pre_swab_drugs_charts(result),
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
            "pre_swab_drugs_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return
        error_message = self._report_service.export_pre_swab_drugs_report_pdf(
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
            build_pre_swab_drugs_charts(self._result),
        )
