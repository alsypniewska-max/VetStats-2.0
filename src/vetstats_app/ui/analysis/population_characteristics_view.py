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

from vetstats_app.analysis.chart_specs import build_population_characteristics_charts
from vetstats_app.analysis.population_characteristics import (
    PopulationCharacteristicsResult,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.population_characteristics_service import (
    PopulationCharacteristicsService,
)
from vetstats_app.ui.analysis.chart_widgets import build_chart_section

MODULE_TITLE = "Charakterystyka populacji pacjentów"


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


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
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.ResizeMode.Stretch
    )
    for row_index, (metric, value) in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(metric))
        table.setItem(row_index, 1, QTableWidgetItem(value))
    return table


class PopulationCharacteristicsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = PopulationCharacteristicsService().analyze()
        result = self._result
        charts = build_population_characteristics_charts(result)

        module_title = QLabel(MODULE_TITLE)

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
                "Ta sekcja przedstawia ogólną charakterystykę populacji pacjentów "
                "na podstawie wczytanych danych."
            )
        )
        summary_layout.addWidget(QLabel(build_summary_details(result)))
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

        interpretation_group = QGroupBox("Interpretacja")
        interpretation_layout = QVBoxLayout(interpretation_group)
        interpretation_layout.addWidget(QLabel(build_interpretation_summary(result)))
        content_layout.addWidget(interpretation_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(module_title)
        layout.addLayout(action_bar)
        layout.addWidget(scroll_area, stretch=1)
