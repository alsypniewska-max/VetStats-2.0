from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QHeaderView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.chart_specs import build_population_characteristics_charts
from vetstats_app.analysis.population_characteristics import (
    PopulationCharacteristicsResult,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.population_characteristics_service import (
    PopulationCharacteristicsService,
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


def _configure_population_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_population_table(table: QTableWidget) -> None:
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


def _build_counts_table(result: PopulationCharacteristicsResult) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(2)
    table.setHorizontalHeaderLabels(["Metryka", "Wartość"])
    rows = [
        ("Liczba pacjentów", str(result.total_patients)),
        ("Liczba rekordów", str(result.total_records)),
        ("Liczba gatunków", str(result.species_count)),
    ]
    table.setRowCount(len(rows))
    _configure_population_table(table)
    for row_index, (metric, value) in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(metric))
        table.setItem(row_index, 1, QTableWidgetItem(value))
    _finalize_population_table(table)
    return table


class PopulationCharacteristicsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = PopulationCharacteristicsService().analyze()
        self._report_service = AnalysisReportService()
        result = self._result
        charts = build_population_characteristics_charts(result)

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
                "Ta sekcja przedstawia ogólną charakterystykę populacji pacjentów "
                "na podstawie wczytanych danych."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        counts_group = QGroupBox("Podstawowe liczby")
        counts_layout = QVBoxLayout(counts_group)
        counts_layout.addWidget(_build_counts_table(result))
        content_layout.addWidget(counts_group)

        content_layout.addWidget(
            build_chart_section(
                "Wykresy populacji",
                charts,
                empty_message=(
                    "Brak danych do wygenerowania wykresów charakterystyki populacji."
                ),
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
            "population_characteristics_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_population_characteristics_report_pdf(
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
            build_population_characteristics_charts(self._result),
        )
