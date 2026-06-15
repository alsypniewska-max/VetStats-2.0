from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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

from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_CODE_MAPPING,
    DiagnosisFrequencyResult,
    build_interpretation_summary,
)
from vetstats_app.services.diagnosis_frequency_service import DiagnosisFrequencyService


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


class DiagnosisFrequencyView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        result = DiagnosisFrequencyService().analyze()

        module_title = QLabel("Analiza częstości rozpoznań")

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")

        action_bar = QHBoxLayout()
        action_bar.addWidget(generate_report_button)
        action_bar.addWidget(export_charts_button)
        action_bar.addStretch()

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

        mapping_group = QGroupBox("Mapowanie kodów rozpoznań")
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_table = QTableWidget()
        mapping_table.setColumnCount(2)
        mapping_table.setHorizontalHeaderLabels(["Kod", "Rozpoznanie"])
        mapping_table.setRowCount(len(DIAGNOSIS_CODE_MAPPING))
        _configure_reference_table(mapping_table)
        mapping_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for row, (code, diagnosis) in enumerate(DIAGNOSIS_CODE_MAPPING):
            mapping_table.setItem(row, 0, QTableWidgetItem(code))
            mapping_table.setItem(row, 1, QTableWidgetItem(diagnosis))
        mapping_layout.addWidget(mapping_table)
        content_layout.addWidget(mapping_group)

        frequency_group = QGroupBox("Częstość rozpoznań")
        frequency_layout = QVBoxLayout(frequency_group)
        frequency_layout.addWidget(self._build_frequency_table(result))
        content_layout.addWidget(frequency_group)

        chart_group = QGroupBox("Wykres częstości")
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.addWidget(
            QLabel("Placeholder: wykres częstości rozpoznań.")
        )
        content_layout.addWidget(chart_group)

        interpretation_group = QGroupBox("Interpretacja")
        interpretation_layout = QVBoxLayout(interpretation_group)
        interpretation_layout.addWidget(
            QLabel(build_interpretation_summary(result))
        )
        content_layout.addWidget(interpretation_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(module_title)
        layout.addLayout(action_bar)
        layout.addWidget(scroll_area, stretch=1)

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
        _configure_reference_table(table)
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        for row_index, row in enumerate(result.frequencies):
            table.setItem(row_index, 0, QTableWidgetItem(row.code))
            table.setItem(row_index, 1, QTableWidgetItem(row.label))
            table.setItem(row_index, 2, QTableWidgetItem(str(row.count)))
            table.setItem(row_index, 3, QTableWidgetItem(f"{row.percentage:.1f}"))

        return table
