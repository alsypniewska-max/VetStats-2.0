from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from pathlib import Path

from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_CODE_MAPPING,
    DiagnosisFrequencyResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
)
from vetstats_app.analysis.chart_specs import build_diagnosis_frequency_charts
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.diagnosis_frequency_service import DiagnosisFrequencyService
from vetstats_app.ui.analysis.chart_widgets import build_chart_section
from vetstats_app.ui.analysis.interpretation_panel import build_interpretation_section
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
)


def _configure_diagnosis_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_diagnosis_table(table: QTableWidget) -> None:
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


def _build_descriptive_stats_group(result: DiagnosisFrequencyResult) -> QGroupBox:
    block = build_descriptive_stats_block(result)
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)

    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_diagnosis_table(table)

    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    _finalize_diagnosis_table(table)
    layout.addWidget(table)
    return group


class DiagnosisFrequencyView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = DiagnosisFrequencyService().analyze()
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
                "Moduł przedstawia analizę częstości rozpoznań na podstawie tabeli "
                "clinical oraz pola type_of_ulcer."
            )
        )
        summary_layout.addWidget(QLabel(self._build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(_build_descriptive_stats_group(result))

        mapping_group = QGroupBox("Mapowanie kodów rozpoznań")
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_table = QTableWidget()
        mapping_table.setColumnCount(2)
        mapping_table.setHorizontalHeaderLabels(["Kod", "Rozpoznanie"])
        mapping_table.setRowCount(len(DIAGNOSIS_CODE_MAPPING))
        _configure_diagnosis_table(mapping_table)
        for row, (code, diagnosis) in enumerate(DIAGNOSIS_CODE_MAPPING):
            mapping_table.setItem(row, 0, QTableWidgetItem(code))
            mapping_table.setItem(row, 1, QTableWidgetItem(diagnosis))
        _finalize_diagnosis_table(mapping_table)
        mapping_layout.addWidget(mapping_table)
        content_layout.addWidget(mapping_group)

        frequency_group = QGroupBox("Częstość rozpoznań")
        frequency_layout = QVBoxLayout(frequency_group)
        frequency_layout.addWidget(self._build_frequency_table(result))
        content_layout.addWidget(frequency_group)

        chart_group = build_chart_section(
            "Wykres częstości",
            build_diagnosis_frequency_charts(result),
            empty_message="Brak danych do wygenerowania wykresu częstości rozpoznań.",
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
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Generuj raport",
            "diagnosis_frequency_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_diagnosis_frequency_report_pdf(
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


    def _build_summary_details(self, result: DiagnosisFrequencyResult) -> str:
        if not result.is_success:
            return result.error_message or "Nie udało się wczytać danych clinical."

        return (
            f"Źródło danych: {result.source_label}. "
            f"Przeanalizowano {result.included_cases} z {result.total_cases} przypadków; "
            f"wykluczono {result.excluded_cases} wierszy z pustymi, xxx "
            f"lub nieprawidłowymi kodami type_of_ulcer."
        )

    def _build_frequency_table(self, result: DiagnosisFrequencyResult) -> QWidget:
        if not result.is_success:
            return QLabel(result.error_message or "Nie udało się obliczyć częstości rozpoznań.")

        if result.included_cases == 0:
            return QLabel("Brak przypadków z prawidłowym kodem type_of_ulcer do analizy.")

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Kod", "Rozpoznanie", "Liczba", "Udział (%)"])
        table.setRowCount(len(result.frequencies))
        _configure_diagnosis_table(table)

        for row_index, row in enumerate(result.frequencies):
            table.setItem(row_index, 0, QTableWidgetItem(row.code))
            table.setItem(row_index, 1, QTableWidgetItem(row.label))
            table.setItem(row_index, 2, QTableWidgetItem(str(row.count)))
            table.setItem(row_index, 3, QTableWidgetItem(f"{row.percentage:.1f}"))

        _finalize_diagnosis_table(table)
        return table
