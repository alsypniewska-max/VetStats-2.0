from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QHBoxLayout,
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

from vetstats_app.analysis.microbiology_results import (
    BacteriaFrequencyRow,
    MicrobiologyResultsResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_matching_details,
    build_summary_details,
)
from vetstats_app.analysis.chart_specs import build_microbiology_results_charts
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.microbiology_results_service import MicrobiologyResultsService
from vetstats_app.ui.analysis.chart_widgets import build_chart_section
from vetstats_app.ui.analysis.interpretation_panel import build_interpretation_section
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
)

MODULE_TITLE = "Analiza wyników mikrobiologicznych"


def _configure_microbiology_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_microbiology_table(table: QTableWidget) -> None:
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


def _build_descriptive_stats_group(result: MicrobiologyResultsResult) -> QGroupBox:
    block = build_descriptive_stats_block(result)
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)

    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_microbiology_table(table)

    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    _finalize_microbiology_table(table)
    layout.addWidget(table)
    return group


def _build_bacteria_table(rows: tuple[BacteriaFrequencyRow, ...]) -> QWidget:
    if not rows:
        return QLabel("Brak dodatnich izolacji bakteryjnych w dopasowanych wynikach.")

    table = QTableWidget()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["Bakteria", "Liczba", "Udział (%)"])
    table.setRowCount(len(rows))
    _configure_microbiology_table(table)

    for row_index, row in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(row.bacteria))
        table.setItem(row_index, 1, QTableWidgetItem(str(row.count)))
        table.setItem(row_index, 2, QTableWidgetItem(f"{row.percentage:.1f}"))

    _finalize_microbiology_table(table)
    return table


def _section_with_widget(title: str, widget: QWidget) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(widget)
    return group


def _section_with_text(title: str, text: str) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(QLabel(text))
    return group


class MicrobiologyResultsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = MicrobiologyResultsService().analyze()
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
            QLabel(
                "Moduł przedstawia wyniki mikrobiologiczne: częstotliwość bakterii, "
                "wyniki negatywne oraz dopasowanie wyników micro do wizyt clinical."
            )
        )
        summary_layout.addWidget(QLabel(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(_build_descriptive_stats_group(result))

        content_layout.addWidget(
            _section_with_widget(
                "Najczęściej izolowane bakterie i wyniki negatywne",
                self._build_bacteria_section(result),
            )
        )

        content_layout.addWidget(
            _section_with_text(
                "Dopasowanie wyniku mikrobiologicznego do wizyty",
                build_matching_details(result),
            )
        )

        content_layout.addWidget(
            build_chart_section(
                "Wykres wyników mikrobiologicznych",
                build_microbiology_results_charts(result),
                empty_message="Brak danych do wygenerowania wykresu wyników mikrobiologicznych.",
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
            "microbiology_results_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_microbiology_results_report_pdf(
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


    def _build_bacteria_section(self, result: MicrobiologyResultsResult) -> QWidget:
        if not result.is_success:
            return QLabel(
                result.error_message
                or "Nie udało się obliczyć wyników mikrobiologicznych."
            )

        if result.matching.matched_pairs == 0:
            return QLabel("Brak dopasowanych par clinical–micro do analizy bakterii.")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            QLabel(
                f"Dodatnie izolacje: {result.included_isolates}. "
                f"Wyniki negatywne: {result.negative_count} "
                f"({result.negative_percentage:.1f}% ważnych obserwacji bakteryjnych). "
                "W częstotliwości bakterii wykluczono wartości xxx, puste i negative."
            )
        )
        layout.addWidget(_build_bacteria_table(result.bacteria_frequencies))
        return container
