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

from vetstats_app.analysis.chart_specs import build_procedure_diagnosis_relationship_charts
from vetstats_app.analysis.procedure_diagnosis_relationship import (
    ProcedureDiagnosisRelationshipResult,
    SECTION_TITLE,
    SUMMARY_RELATIONSHIP_TABLE_COLUMNS,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
    build_table_details,
    format_top_diagnoses,
    observed_procedure_categories,
    procedure_display_label,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.procedure_diagnosis_relationship_service import (
    ProcedureDiagnosisRelationshipService,
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

MODULE_TITLE = SECTION_TITLE


def _configure_procedure_diagnosis_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_procedure_diagnosis_table(table: QTableWidget) -> None:
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


def _build_descriptive_stats_group(
    result: ProcedureDiagnosisRelationshipResult,
) -> QGroupBox:
    block = build_descriptive_stats_block(result)
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)

    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_procedure_diagnosis_table(table)

    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    _finalize_procedure_diagnosis_table(table)
    layout.addWidget(table)
    return group


def _build_relationship_table(
    result: ProcedureDiagnosisRelationshipResult,
) -> QWidget:
    if not result.is_success:
        return build_wrapped_text_label(
            result.error_message
            or "Nie udało się obliczyć powiązania type_of_surgery z type_of_ulcer."
        )

    if result.included_cases == 0:
        return build_wrapped_text_label(
            "Brak wierszy clinical z jednocześnie prawidłowym type_of_surgery "
            "i type_of_ulcer do analizy."
        )

    visible_categories = observed_procedure_categories(result)
    if not visible_categories:
        return build_wrapped_text_label(
            "Brak kategorii type_of_surgery z dopasowanymi wierszami clinical "
            "i type_of_ulcer."
        )

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(list(SUMMARY_RELATIONSHIP_TABLE_COLUMNS))
    table.setRowCount(len(visible_categories))
    _configure_procedure_diagnosis_table(table)

    for row_index, category in enumerate(visible_categories):
        table.setItem(row_index, 0, QTableWidgetItem(category.code))
        table.setItem(row_index, 1, QTableWidgetItem(procedure_display_label(category.code)))
        table.setItem(row_index, 2, QTableWidgetItem(str(category.clinical_rows)))
        table.setItem(
            row_index,
            3,
            QTableWidgetItem(format_top_diagnoses(category.top_diagnoses)),
        )

    _finalize_procedure_diagnosis_table(table)
    return table


def _build_pair_detail_table(
    result: ProcedureDiagnosisRelationshipResult,
) -> QWidget:
    if not result.is_success:
        return build_wrapped_text_label(
            result.error_message
            or "Nie udało się obliczyć par zabieg — rozpoznanie."
        )

    if result.included_cases == 0 or not result.procedure_ulcer_pairs:
        return build_wrapped_text_label(
            "Brak par zabieg — rozpoznanie do wyświetlenia."
        )

    table = QTableWidget()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(
        ["Kategoria zabiegu", "Rozpoznanie", "Liczba wierszy"]
    )
    table.setRowCount(len(result.procedure_ulcer_pairs))
    _configure_procedure_diagnosis_table(table)

    for row_index, pair in enumerate(result.procedure_ulcer_pairs):
        table.setItem(row_index, 0, QTableWidgetItem(pair.procedure_label))
        table.setItem(row_index, 1, QTableWidgetItem(pair.ulcer_label))
        table.setItem(row_index, 2, QTableWidgetItem(str(pair.count)))

    _finalize_procedure_diagnosis_table(table)
    return table


def _section_with_widget(title: str, widget: QWidget) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(widget)
    return group


class ProcedureDiagnosisRelationshipView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = ProcedureDiagnosisRelationshipService().analyze()
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
                "Moduł analizuje wyłącznie tabelę clinical i łączy pole "
                "type_of_surgery z polem type_of_ulcer. Wiersze bez prawidłowego "
                "kodu type_of_surgery lub type_of_ulcer są pomijane."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(_build_descriptive_stats_group(result))

        relationship_group = QGroupBox(SECTION_TITLE)
        relationship_layout = QVBoxLayout(relationship_group)
        table_note = build_table_details(result)
        if table_note:
            relationship_layout.addWidget(build_wrapped_text_label(table_note))
        relationship_layout.addWidget(_build_relationship_table(result))
        content_layout.addWidget(relationship_group)

        content_layout.addWidget(
            _section_with_widget(
                "Szczegółowe pary zabieg — rozpoznanie",
                _build_pair_detail_table(result),
            )
        )

        content_layout.addWidget(
            build_chart_section(
                "Wykresy zależności między zabiegiem a rozpoznaniem",
                build_procedure_diagnosis_relationship_charts(result),
                empty_message=(
                    "Brak danych do wygenerowania wykresów zależności "
                    "między zabiegiem a rozpoznaniem."
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
            "procedure_diagnosis_relationship_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_procedure_diagnosis_relationship_report_pdf(
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
            build_procedure_diagnosis_relationship_charts(self._result),
        )
