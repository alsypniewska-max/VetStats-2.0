from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.chart_specs import build_resistance_over_time_charts
from vetstats_app.analysis.resistance_over_time import (
    ResistanceOverTimeResult,
    YearlyResistanceSummary,
    build_descriptive_stats_block,
    build_inclusion_details,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.resistance_over_time_service import ResistanceOverTimeService
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

MODULE_TITLE = "Analiza oporności bakterii w czasie"


def _configure_resistance_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_resistance_table(table: QTableWidget) -> None:
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


def _build_descriptive_stats_group(result: ResistanceOverTimeResult) -> QGroupBox:
    block = build_descriptive_stats_block(result)
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)

    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_resistance_table(table)

    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    _finalize_resistance_table(table)
    layout.addWidget(table)
    return group


def _build_yearly_overview_table(
    summaries: tuple[YearlyResistanceSummary, ...],
) -> QWidget:
    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(
        ["Rok", "Obserwacje", "Najczęstsza bakteria", "Liczba"]
    )
    table.setRowCount(len(summaries))
    _configure_resistance_table(table)

    for row_index, summary in enumerate(summaries):
        table.setItem(row_index, 0, QTableWidgetItem(str(summary.year)))
        table.setItem(
            row_index,
            1,
            QTableWidgetItem(str(summary.included_observations)),
        )
        bacteria_label = summary.most_common_bacteria or "—"
        table.setItem(row_index, 2, QTableWidgetItem(bacteria_label))
        table.setItem(
            row_index,
            3,
            QTableWidgetItem(str(summary.most_common_bacteria_count)),
        )

    _finalize_resistance_table(table)
    return table


def _build_sensitivity_table(result: ResistanceOverTimeResult) -> QWidget:
    if not result.has_sensitivity_data:
        return build_wrapped_text_label("Brak kolumn wrażliwości w tabeli micro.")

    if result.exclusions.included_total == 0:
        return build_wrapped_text_label("Brak obserwacji do analizy wrażliwości.")

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Rok", "+++", "+", "0"])
    table.setRowCount(len(result.yearly_summaries))
    _configure_resistance_table(table)

    for row_index, summary in enumerate(result.yearly_summaries):
        table.setItem(row_index, 0, QTableWidgetItem(str(summary.year)))
        counts = {row.code: row.count for row in summary.sensitivity_counts}
        table.setItem(row_index, 1, QTableWidgetItem(str(counts.get("+++", 0))))
        table.setItem(row_index, 2, QTableWidgetItem(str(counts.get("+", 0))))
        table.setItem(row_index, 3, QTableWidgetItem(str(counts.get("0", 0))))

    _finalize_resistance_table(table)

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(
        build_wrapped_text_label(
            "Zagregowane roczne podsumowanie kategorii wrażliwości (+++, +, 0) "
            "z kolumn growth i antybiotyków dla obserwacji bakteryjnych."
        )
    )
    layout.addWidget(table)
    return container


def _section_with_widget(title: str, widget: QWidget) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(widget)
    return group


def _section_with_text(title: str, text: str) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(build_wrapped_text_label(text))
    return group


class ResistanceOverTimeView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = ResistanceOverTimeService().analyze()
        self._report_service = AnalysisReportService()
        result = self._result

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")
        self._action_bar_widget = build_module_action_bar(
            generate_report_button,
            export_charts_button,
        )

        generate_report_button.clicked.connect(self._on_generate_report)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            build_wrapped_text_label(
                "Moduł przedstawia oporność bakterii w czasie wyłącznie "
                "na podstawie tabeli micro."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(_build_descriptive_stats_group(result))

        content_layout.addWidget(
            _section_with_widget(
                "Zakres czasowy analizy",
                _build_yearly_overview_table(result.yearly_summaries)
                if result.is_success
                else build_wrapped_text_label(
                    result.error_message or "Nie udało się obliczyć zakresu czasowego."
                ),
            )
        )

        content_layout.addWidget(
            _section_with_text(
                "Kryteria włączenia danych",
                build_inclusion_details(result),
            )
        )

        content_layout.addWidget(
            _section_with_widget(
                "Ogólne podsumowanie wrażliwości rocznej",
                _build_sensitivity_table(result),
            )
        )

        content_layout.addWidget(
            build_chart_section(
                "Wykresy oporności w czasie",
                build_resistance_over_time_charts(result),
                empty_message="Brak danych do wygenerowania wykresów oporności w czasie.",
            )
        )

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
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Generuj raport",
            "resistance_over_time_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_resistance_over_time_report_pdf(
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
