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

from vetstats_app.analysis.diagnosis_culture_relationship import (
    DiagnosisCultureRelationshipResult,
    UlcerCategoryCultureSummary,
    build_interpretation_summary,
    build_matching_details,
    build_summary_details,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.diagnosis_culture_relationship_service import (
    DiagnosisCultureRelationshipService,
)
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
    stretch_column,
)

MODULE_TITLE = "Powiązanie rozpoznań z wynikami posiewu"


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


def _build_category_cases_table(
    categories: tuple[UlcerCategoryCultureSummary, ...],
) -> QWidget:
    table = QTableWidget()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["Kod", "Kategoria wrzodu", "Liczba przypadków"])
    table.setRowCount(len(categories))
    configure_reference_table(table)
    stretch_column(table, 1)

    for row_index, category in enumerate(categories):
        table.setItem(row_index, 0, QTableWidgetItem(category.code))
        table.setItem(row_index, 1, QTableWidgetItem(category.label))
        table.setItem(row_index, 2, QTableWidgetItem(str(category.matched_cases)))

    finalize_reference_table(table)
    return table


def _build_bacteria_by_category_table(
    categories: tuple[UlcerCategoryCultureSummary, ...],
) -> QWidget:
    rows: list[tuple[str, str, int]] = []
    for category in categories:
        if category.matched_cases == 0:
            continue
        if not category.bacteria_rows:
            rows.append((category.label, "—", 0))
            continue
        for bacteria_row in category.bacteria_rows:
            rows.append((category.label, bacteria_row.bacteria, bacteria_row.count))

    if not rows:
        return QLabel("Brak bakterii do wyświetlenia w dopasowanych kategoriach wrzodu.")

    table = QTableWidget()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["Kategoria wrzodu", "Bakteria", "Liczba"])
    table.setRowCount(len(rows))
    configure_reference_table(table)
    stretch_column(table, 0)
    stretch_column(table, 1)

    for row_index, (category_label, bacteria, count) in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(category_label))
        table.setItem(row_index, 1, QTableWidgetItem(bacteria))
        table.setItem(row_index, 2, QTableWidgetItem(str(count)))

    finalize_reference_table(table)
    return table


class DiagnosisCultureRelationshipView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = DiagnosisCultureRelationshipService().analyze()
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
                "Moduł łączy kategorie type_of_ulcer z wynikami posiewu "
                "na podstawie dopasowanych par clinical–micro."
            )
        )
        summary_layout.addWidget(QLabel(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(
            _section_with_widget(
                "Przypadki według kategorii wrzodu",
                _build_category_cases_table(result.categories)
                if result.is_success
                else QLabel(result.error_message or "Nie udało się obliczyć kategorii wrzodu."),
            )
        )

        content_layout.addWidget(
            _section_with_widget(
                "Bakterie w poszczególnych kategoriach wrzodu",
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
            _section_with_text(
                "Interpretacja",
                build_interpretation_summary(result),
            )
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
            "diagnosis_culture_relationship_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._report_service.export_diagnosis_culture_relationship_report_pdf(
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


    def _build_bacteria_section(self, result: DiagnosisCultureRelationshipResult) -> QWidget:
        if not result.is_success:
            return QLabel(
                result.error_message
                or "Nie udało się obliczyć bakterii w kategoriach wrzodu."
            )

        if result.matching.matched_pairs == 0:
            return QLabel("Brak dopasowanych par clinical–micro do analizy bakterii.")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            QLabel(
                "Tabela pokazuje izolowane bakterie w dopasowanych przypadkach "
                "dla każdej kategorii type_of_ulcer (x jako other). "
                "Wykluczono puste i xxx."
            )
        )
        layout.addWidget(_build_bacteria_by_category_table(result.categories))
        return container
