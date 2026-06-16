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
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
    stretch_column,
)


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
    configure_reference_table(table)
    stretch_column(table, 1)
    for row_index, (metric, value) in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(metric))
        table.setItem(row_index, 1, QTableWidgetItem(value))
    finalize_reference_table(table)
    return table


class PopulationCharacteristicsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = PopulationCharacteristicsService().analyze()
        result = self._result
        charts = build_population_characteristics_charts(result)

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")
        self._action_bar_widget = build_module_action_bar(
            generate_report_button,
            export_charts_button,
        )

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area, stretch=1)

    def action_bar_widget(self) -> QWidget:
        return self._action_bar_widget
