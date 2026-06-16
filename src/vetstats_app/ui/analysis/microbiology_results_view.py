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

from vetstats_app.analysis.microbiology_results import (
    BacteriaFrequencyRow,
    MicrobiologyResultsResult,
    build_interpretation_summary,
    build_matching_details,
    build_summary_details,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.microbiology_results_service import MicrobiologyResultsService

MODULE_TITLE = "Analiza wyników mikrobiologicznych"


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


def _build_bacteria_table(rows: tuple[BacteriaFrequencyRow, ...]) -> QWidget:
    if not rows:
        return QLabel("Brak dodatnich izolacji bakteryjnych w dopasowanych wynikach.")

    table = QTableWidget()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["Bakteria", "Liczba", "Udział (%)"])
    table.setRowCount(len(rows))
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeMode.Stretch
    )

    for row_index, row in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(row.bacteria))
        table.setItem(row_index, 1, QTableWidgetItem(str(row.count)))
        table.setItem(row_index, 2, QTableWidgetItem(f"{row.percentage:.1f}"))

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
                "Moduł przedstawia wyniki mikrobiologiczne: częstotliwość bakterii, "
                "wyniki negatywne oraz dopasowanie wyników micro do wizyt clinical."
            )
        )
        summary_layout.addWidget(QLabel(build_summary_details(result)))
        content_layout.addWidget(summary_group)

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
