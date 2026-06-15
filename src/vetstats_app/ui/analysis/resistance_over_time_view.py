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

from vetstats_app.analysis.resistance_over_time import (
    ResistanceOverTimeResult,
    YearlyResistanceSummary,
    build_inclusion_details,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.resistance_over_time_service import ResistanceOverTimeService

MODULE_TITLE = "Analiza oporności bakterii w czasie"


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


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


def _build_yearly_overview_table(
    summaries: tuple[YearlyResistanceSummary, ...],
) -> QWidget:
    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(
        ["Rok", "Obserwacje", "Najczęstsza bakteria", "Liczba"]
    )
    table.setRowCount(len(summaries))
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(
        2, QHeaderView.ResizeMode.Stretch
    )

    for row_index, summary in enumerate(summaries):
        table.setItem(row_index, 0, QTableWidgetItem(str(summary.year)))
        table.setItem(
            row_index,
            1,
            QTableWidgetItem(str(summary.included_observations)),
        )
        bacteria_label = summary.most_common_bacteria or "—"
        table.setItem(row_index, 2, QTableWidgetItem(bacteria_label))
        table.setItem(
            row_index,
            3,
            QTableWidgetItem(str(summary.most_common_bacteria_count)),
        )

    return table


def _build_sensitivity_table(result: ResistanceOverTimeResult) -> QWidget:
    if not result.has_sensitivity_data:
        return QLabel("Brak kolumn wrażliwości w tabeli micro.")

    if result.exclusions.included_total == 0:
        return QLabel("Brak obserwacji do analizy wrażliwości.")

    table = QTableWidget()
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(["Rok", "+++", "+", "0", "x"])
    table.setRowCount(len(result.yearly_summaries))
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeMode.Stretch
    )

    for row_index, summary in enumerate(result.yearly_summaries):
        table.setItem(row_index, 0, QTableWidgetItem(str(summary.year)))
        counts = {row.code: row.count for row in summary.sensitivity_counts}
        table.setItem(row_index, 1, QTableWidgetItem(str(counts.get("+++", 0))))
        table.setItem(row_index, 2, QTableWidgetItem(str(counts.get("+", 0))))
        table.setItem(row_index, 3, QTableWidgetItem(str(counts.get("0", 0))))
        table.setItem(row_index, 4, QTableWidgetItem(str(counts.get("x", 0))))

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(
        QLabel(
            "Zagregowane roczne podsumowanie kategorii wrażliwości (+++, +, 0, x) "
            "z kolumn growth i antybiotyków. To nie jest analiza w podziale na gatunki bakterii."
        )
    )
    layout.addWidget(table)
    return container


class ResistanceOverTimeView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        result = ResistanceOverTimeService().analyze()

        title_label = QLabel(MODULE_TITLE)

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
                "Moduł przedstawia oporność bakterii w czasie wyłącznie "
                "na podstawie tabeli micro."
            )
        )
        summary_layout.addWidget(QLabel(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        content_layout.addWidget(
            _section_with_widget(
                "Zakres czasowy analizy",
                _build_yearly_overview_table(result.yearly_summaries)
                if result.is_success
                else QLabel(result.error_message or "Nie udało się obliczyć zakresu czasowego."),
            )
        )

        content_layout.addWidget(
            _section_with_text(
                "Kryteria włączenia danych",
                build_inclusion_details(result),
            )
        )

        content_layout.addWidget(
            _section_with_widget(
                "Ogólne podsumowanie wrażliwości rocznej",
                _build_sensitivity_table(result),
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
