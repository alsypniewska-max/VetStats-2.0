from PyQt6.QtCore import Qt
from pathlib import Path

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QFileDialog,
    QPushButton,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.treatment_groups import (
    TreatmentCategoryRow,
    TreatmentGroupsResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.analysis.chart_specs import build_treatment_groups_charts
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.treatment_groups_service import TreatmentGroupsService
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

MODULE_TITLE = "Analiza leczenia w grupach pacjentów"


def _configure_treatment_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_treatment_table(table: QTableWidget) -> None:
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


def _build_descriptive_stats_group(result: TreatmentGroupsResult) -> QGroupBox:
    block = build_descriptive_stats_block(result)
    group = QGroupBox(block.title)
    layout = QVBoxLayout(group)

    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_treatment_table(table)

    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    _finalize_treatment_table(table)
    layout.addWidget(table)
    return group


def _build_category_table(
    rows: tuple[TreatmentCategoryRow, ...],
    *,
    empty_message: str,
) -> QWidget:
    if not rows:
        return build_wrapped_text_label(empty_message)

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Kod", "Kategoria", "Liczba", "Udział (%)"])
    table.setRowCount(len(rows))
    _configure_treatment_table(table)

    for row_index, row in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(row.code))
        table.setItem(row_index, 1, QTableWidgetItem(row.label))
        table.setItem(row_index, 2, QTableWidgetItem(str(row.count)))
        table.setItem(row_index, 3, QTableWidgetItem(f"{row.percentage:.1f}"))

    _finalize_treatment_table(table)
    return table


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


class TreatmentGroupsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = TreatmentGroupsService().analyze()
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

        summary_text = (
            "Moduł przedstawia analizę wzorców leczenia na podstawie wierszy "
            "z tabeli clinical."
        )
        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(build_wrapped_text_label(summary_text))
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(_build_descriptive_stats_group(result))

        content_layout.addWidget(
            _section_with_widget(
                "Podział przypadków według typu leczenia",
                self._build_pharmacology_section(result),
            )
        )
        content_layout.addWidget(
            _section_with_widget(
                "Leczenie miejscowe i ogólne",
                self._build_topical_section(result),
            )
        )
        content_layout.addWidget(
            _section_with_widget(
                "Skuteczność leczenia wrzodów",
                self._build_ulcer_success_section(result),
            )
        )
        content_layout.addWidget(
            build_chart_section(
                "Wykresy leczenia",
                build_treatment_groups_charts(result),
                empty_message="Brak danych do wygenerowania wykresów leczenia.",
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
            "treatment_groups_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_treatment_groups_report_pdf(
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
            build_treatment_groups_charts(self._result),
        )


    def _build_pharmacology_section(self, result: TreatmentGroupsResult) -> QWidget:
        if not result.is_success:
            return build_wrapped_text_label(
                result.error_message or "Nie udało się obliczyć podziału leczenia."
            )

        if result.pharmacology_included_cases == 0:
            return build_wrapped_text_label(
                "Brak przypadków z prawidłowym kodem farmacology_surgery do analizy."
            )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            build_wrapped_text_label(
                f"Przeanalizowano {result.pharmacology_included_cases} z {result.total_cases} "
                f"przypadków; wykluczono {result.pharmacology_excluded_cases} wierszy "
                f"z pustymi, xxx lub nieprawidłowymi kodami farmacology_surgery."
            )
        )
        layout.addWidget(
            _build_category_table(
                result.pharmacology_rows,
                empty_message="Brak danych farmacology_surgery.",
            )
        )
        return container

    def _build_topical_section(self, result: TreatmentGroupsResult) -> QWidget:
        if not result.is_success:
            return build_wrapped_text_label(
                result.error_message
                or "Nie udało się obliczyć analizy topical_systemic."
            )

        if result.topical_included_cases == 0:
            return build_wrapped_text_label(
                "Brak przypadków z prawidłowym kodem topical_systemic do analizy."
            )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            build_wrapped_text_label(
                f"Przeanalizowano {result.topical_included_cases} z {result.total_cases} "
                f"przypadków; wykluczono {result.topical_excluded_cases} wierszy "
                f"z pustymi, xxx lub nieprawidłowymi kodami topical_systemic."
            )
        )
        layout.addWidget(
            _build_category_table(
                result.topical_rows,
                empty_message="Brak danych topical_systemic.",
            )
        )
        return container

    def _build_ulcer_success_section(self, result: TreatmentGroupsResult) -> QWidget:
        if not result.is_success:
            return build_wrapped_text_label(
                result.error_message
                or "Nie udało się obliczyć skuteczności leczenia wrzodów."
            )

        ulcer_success = result.ulcer_success
        if ulcer_success.eligible_cases == 0:
            return build_wrapped_text_label(
                "Brak przypadków wrzodowych (type_of_ulcer inne niż x i xxx) "
                "do oceny skuteczności leczenia."
            )

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Metryka", "Wartość"])
        table.setRowCount(5)
        _configure_treatment_table(table)

        metrics = [
            ("Przypadki wrzodowe (bez x i xxx)", str(ulcer_success.eligible_cases)),
            ("Wykluczone (how_ended = continuation)", str(ulcer_success.excluded_continuation)),
            ("Ocenione przypadki", str(ulcer_success.evaluated_cases)),
            ("Zakończone jako good", str(ulcer_success.success_count)),
            ("Skuteczność (%)", f"{ulcer_success.success_rate:.1f}"),
        ]
        for row_index, (metric, value) in enumerate(metrics):
            table.setItem(row_index, 0, QTableWidgetItem(metric))
            table.setItem(row_index, 1, QTableWidgetItem(value))
        _finalize_treatment_table(table)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            build_wrapped_text_label(
                "Skuteczność liczona tylko dla prawdziwych kategorii wrzodu "
                "(s, e, p, n, m, sceed). Wiersze z how_ended = continuation "
                "są wykluczone ze statystyki skuteczności."
            )
        )
        layout.addWidget(table)
        return container
