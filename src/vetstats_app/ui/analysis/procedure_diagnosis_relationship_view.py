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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.procedure_diagnosis_relationship import (
    ProcedureDiagnosisRelationshipResult,
    build_interpretation_summary,
    build_summary_details,
    build_table_details,
    format_top_diagnoses,
    observed_procedure_categories,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.procedure_diagnosis_relationship_service import (
    ProcedureDiagnosisRelationshipService,
)

MODULE_TITLE = "Powiązanie type_of_surgery z type_of_ulcer"


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


def _section_with_text(title: str, text: str) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(QLabel(text))
    return group


def _build_relationship_table(
    result: ProcedureDiagnosisRelationshipResult,
) -> QWidget:
    if not result.is_success:
        return QLabel(
            result.error_message
            or "Nie udało się obliczyć powiązania type_of_surgery z type_of_ulcer."
        )

    if result.included_cases == 0:
        return QLabel(
            "Brak wierszy clinical z jednocześnie prawidłowym type_of_surgery "
            "i type_of_ulcer do analizy."
        )

    visible_categories = observed_procedure_categories(result)
    if not visible_categories:
        return QLabel(
            "Brak kategorii type_of_surgery z dopasowanymi wierszami clinical "
            "i type_of_ulcer."
        )

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(
        [
            "Kod type_of_surgery",
            "Kategoria procedury",
            "Liczba wierszy",
            "Najczęstsze kategorie type_of_ulcer",
        ]
    )
    table.setRowCount(len(visible_categories))
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.ResizeMode.Stretch
    )
    table.horizontalHeader().setSectionResizeMode(
        3, QHeaderView.ResizeMode.Stretch
    )

    for row_index, category in enumerate(visible_categories):
        table.setItem(row_index, 0, QTableWidgetItem(category.code))
        table.setItem(row_index, 1, QTableWidgetItem(category.label))
        table.setItem(row_index, 2, QTableWidgetItem(str(category.clinical_rows)))
        table.setItem(
            row_index,
            3,
            QTableWidgetItem(format_top_diagnoses(category.top_diagnoses)),
        )

    return table


class ProcedureDiagnosisRelationshipView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = ProcedureDiagnosisRelationshipService().analyze()
        self._report_service = AnalysisReportService()
        result = self._result

        title_label = QLabel(MODULE_TITLE)

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")

        action_bar = QHBoxLayout()
        action_bar.addWidget(generate_report_button)
        action_bar.addWidget(export_charts_button)
        action_bar.addStretch()

        generate_report_button.clicked.connect(self._on_generate_report)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            QLabel(
                "Moduł analizuje wyłącznie tabelę clinical i łączy pole "
                "type_of_surgery z polem type_of_ulcer. Wiersze bez prawidłowego "
                "kodu type_of_surgery lub type_of_ulcer są pomijane."
            )
        )
        summary_layout.addWidget(QLabel(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        relationship_group = QGroupBox("Powiązanie type_of_surgery z type_of_ulcer")
        relationship_layout = QVBoxLayout(relationship_group)
        table_note = build_table_details(result)
        if table_note:
            relationship_layout.addWidget(QLabel(table_note))
        relationship_layout.addWidget(_build_relationship_table(result))
        content_layout.addWidget(relationship_group)

        content_layout.addWidget(
            _section_with_text(
                "Interpretacja",
                build_interpretation_summary(result),
            )
        )

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(title_label)
        layout.addLayout(action_bar)
        layout.addWidget(scroll_area, stretch=1)

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
