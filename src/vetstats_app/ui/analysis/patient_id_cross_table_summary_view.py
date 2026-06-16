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

from vetstats_app.analysis.patient_id_cross_table_summary import (
    PatientIdCrossTableSummaryResult,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.patient_id_cross_table_summary_service import (
    PatientIdCrossTableSummaryService,
)
from vetstats_app.ui.analysis.interpretation_panel import (
    build_interpretation_section,
    build_wrapped_text_label,
)
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
)

MODULE_TITLE = "Podsumowanie powiązań patient_ID między tabelami"


def _configure_patient_id_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_patient_id_table(table: QTableWidget) -> None:
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


def _section_with_text(title: str, text: str) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(build_wrapped_text_label(text))
    return group


def _build_table_counts_table(result: PatientIdCrossTableSummaryResult) -> QWidget:
    if not result.is_success:
        return build_wrapped_text_label(
            result.error_message
            or "Nie udało się obliczyć liczby unikalnych patient_ID."
        )

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(
        ["Tabela", "Źródło", "Unikalne patient_ID", "Wykluczone wiersze"]
    )
    table.setRowCount(len(result.tables))
    _configure_patient_id_table(table)

    for row_index, entry in enumerate(result.tables):
        table.setItem(row_index, 0, QTableWidgetItem(entry.table_name))
        table.setItem(row_index, 1, QTableWidgetItem(entry.source_label))
        table.setItem(row_index, 2, QTableWidgetItem(str(entry.unique_patient_ids)))
        table.setItem(row_index, 3, QTableWidgetItem(str(entry.excluded_rows)))

    _finalize_patient_id_table(table)
    return table


def _build_pairwise_table(result: PatientIdCrossTableSummaryResult) -> QWidget:
    if not result.is_success:
        return build_wrapped_text_label(
            result.error_message
            or "Nie udało się obliczyć powiązań patient_ID między tabelami."
        )

    table = QTableWidget()
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(
        [
            "Tabela A",
            "Tabela B",
            "Wspólne patient_ID",
            "Tylko w A",
            "Tylko w B",
        ]
    )
    table.setRowCount(len(result.pairwise))
    _configure_patient_id_table(table)

    for row_index, linkage in enumerate(result.pairwise):
        table.setItem(row_index, 0, QTableWidgetItem(linkage.table_a))
        table.setItem(row_index, 1, QTableWidgetItem(linkage.table_b))
        table.setItem(row_index, 2, QTableWidgetItem(str(linkage.shared_count)))
        table.setItem(row_index, 3, QTableWidgetItem(str(linkage.only_in_a)))
        table.setItem(row_index, 4, QTableWidgetItem(str(linkage.only_in_b)))

    _finalize_patient_id_table(table)
    return table


class PatientIdCrossTableSummaryView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = PatientIdCrossTableSummaryService().analyze()
        self._report_service = AnalysisReportService()
        result = self._result

        generate_report_button = QPushButton("Generuj raport")
        self._action_bar_widget = build_module_action_bar(
            generate_report_button,
        )

        generate_report_button.clicked.connect(self._on_generate_report)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            build_wrapped_text_label(
                "Moduł pokazuje automatyczne podsumowanie powiązań między tabelami "
                "patient, clinical i micro na podstawie patient_ID. "
                "To nie jest widok historii pojedynczego pacjenta."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(
            _section_with_widget(
                "Unikalne patient_ID w tabelach",
                _build_table_counts_table(result),
            )
        )

        content_layout.addWidget(
            _section_with_widget(
                "Powiązania patient_ID między parami tabel",
                _build_pairwise_table(result),
            )
        )

        if result.is_success:
            single_only_text = ", ".join(
                f"{entry.table_name}: {entry.count}"
                for entry in result.only_in_single_table
                if entry.count > 0
            )
            coverage_text = (
                f"patient_ID obecne we wszystkich trzech tabelach: "
                f"{result.in_all_three}."
            )
            if single_only_text:
                coverage_text += (
                    f" Identyfikatory obecne wyłącznie w jednej tabeli: "
                    f"{single_only_text}."
                )
            content_layout.addWidget(_section_with_text("Zasięg powiązań", coverage_text))

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
            "patient_id_cross_table_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_patient_id_cross_table_report_pdf(
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


def _section_with_widget(title: str, widget: QWidget) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(widget)
    return group
