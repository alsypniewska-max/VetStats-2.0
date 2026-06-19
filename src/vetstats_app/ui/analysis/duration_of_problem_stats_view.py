from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
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

from vetstats_app.analysis.chart_specs import build_duration_of_problem_stats_charts
from vetstats_app.analysis.clinical_common import format_optional_number
from vetstats_app.analysis.duration_of_problem_stats import (
    DurationOfProblemStatsResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.duration_of_problem_stats_service import (
    DurationOfProblemStatsService,
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

MODULE_TITLE = "Czas trwania problemu przed pierwszą wizytą"


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


def _finalize_descriptive_stats_table(table: QTableWidget) -> None:
    table.setWordWrap(False)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for column_index in range(table.columnCount()):
        header.setSectionResizeMode(
            column_index,
            QHeaderView.ResizeMode.ResizeToContents,
        )

    metrics = table.fontMetrics()
    max_label_width = 0
    for row_index in range(table.rowCount()):
        item = table.item(row_index, 0)
        if item is not None:
            max_label_width = max(
                max_label_width,
                metrics.horizontalAdvance(item.text()),
            )
    if max_label_width > 0:
        table.setColumnWidth(0, max_label_width + 12)

    finalize_reference_table(table)

    total_width = table.frameWidth() * 2
    for column_index in range(table.columnCount()):
        total_width += table.columnWidth(column_index)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
    table.setMaximumWidth(total_width + 8)


class DurationOfProblemStatsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = DurationOfProblemStatsService().analyze()
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
                "Moduł analizuje pole duration_of_problem dla przypadków wrzodowych "
                "w tabeli clinical."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        stats_block = build_descriptive_stats_block(result)
        stats_group = QGroupBox(stats_block.title)
        stats_layout = QVBoxLayout(stats_group)
        stats_table = QTableWidget()
        stats_table.setColumnCount(len(stats_block.columns))
        stats_table.setHorizontalHeaderLabels(list(stats_block.columns))
        stats_table.setRowCount(len(stats_block.rows))
        _configure_table(stats_table)
        for row_index, row in enumerate(stats_block.rows):
            for column_index, value in enumerate(row):
                stats_table.setItem(row_index, column_index, QTableWidgetItem(value))
        _finalize_descriptive_stats_table(stats_table)
        stats_layout.addWidget(stats_table)
        content_layout.addWidget(stats_group)

        ulcer_group = QGroupBox("Czas trwania problemu według typu wrzodu")
        ulcer_layout = QVBoxLayout(ulcer_group)
        ulcer_layout.addWidget(self._build_ulcer_table(result))
        content_layout.addWidget(ulcer_group)

        chart_group = build_chart_section(
            "Wykresy",
            build_duration_of_problem_stats_charts(result),
            empty_message="Brak danych do wygenerowania wykresu.",
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

    def _build_ulcer_table(self, result: DurationOfProblemStatsResult) -> QWidget:
        if not result.is_success or result.included_rows == 0:
            return build_wrapped_text_label(
                result.error_message
                or "Brak przypadków z prawidłowym duration_of_problem do analizy."
            )

        table = QTableWidget()
        headers = [
            "Typ wrzodu",
            "Liczba",
            "Średnia (dni)",
            "Mediana (dni)",
            "P25 (dni)",
            "P75 (dni)",
        ]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(result.by_ulcer_type))
        _configure_table(table)
        for row_index, row in enumerate(result.by_ulcer_type):
            table.setItem(row_index, 0, QTableWidgetItem(row.ulcer_label))
            table.setItem(row_index, 1, QTableWidgetItem(str(row.count)))
            table.setItem(
                row_index,
                2,
                QTableWidgetItem(format_optional_number(row.mean_days)),
            )
            table.setItem(
                row_index,
                3,
                QTableWidgetItem(format_optional_number(row.median_days)),
            )
            table.setItem(
                row_index,
                4,
                QTableWidgetItem(format_optional_number(row.percentile_25_days)),
            )
            table.setItem(
                row_index,
                5,
                QTableWidgetItem(format_optional_number(row.percentile_75_days)),
            )
        _finalize_table(table)
        return table

    def _on_generate_report(self) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Generuj raport",
            "duration_of_problem_stats_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return
        error_message = self._report_service.export_duration_of_problem_stats_report_pdf(
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
            build_duration_of_problem_stats_charts(self._result),
        )
