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

from vetstats_app.analysis.treatment_groups import (
    TreatmentCategoryRow,
    TreatmentGroupsResult,
    build_interpretation_summary,
    build_summary_details,
)
from vetstats_app.services.treatment_groups_service import TreatmentGroupsService

MODULE_TITLE = "Analiza leczenia w grupach pacjentów"


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


def _build_category_table(
    rows: tuple[TreatmentCategoryRow, ...],
    *,
    empty_message: str,
) -> QWidget:
    if not rows:
        return QLabel(empty_message)

    table = QTableWidget()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Kod", "Kategoria", "Liczba", "Udział (%)"])
    table.setRowCount(len(rows))
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.ResizeMode.Stretch
    )

    for row_index, row in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(row.code))
        table.setItem(row_index, 1, QTableWidgetItem(row.label))
        table.setItem(row_index, 2, QTableWidgetItem(str(row.count)))
        table.setItem(row_index, 3, QTableWidgetItem(f"{row.percentage:.1f}"))

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


class TreatmentGroupsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        result = TreatmentGroupsService().analyze()

        title_label = QLabel(MODULE_TITLE)

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")

        action_bar = QHBoxLayout()
        action_bar.addWidget(generate_report_button)
        action_bar.addWidget(export_charts_button)
        action_bar.addStretch()

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_text = (
            "Moduł przedstawia analizę wzorców leczenia na podstawie wierszy "
            "z tabeli clinical."
        )
        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(QLabel(summary_text))
        summary_layout.addWidget(QLabel(build_summary_details(result)))
        content_layout.addWidget(summary_group)

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

    def _build_pharmacology_section(self, result: TreatmentGroupsResult) -> QWidget:
        if not result.is_success:
            return QLabel(result.error_message or "Nie udało się obliczyć podziału leczenia.")

        if result.pharmacology_included_cases == 0:
            return QLabel(
                "Brak przypadków z prawidłowym kodem farmacology_surgery do analizy."
            )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            QLabel(
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
            return QLabel(
                result.error_message
                or "Nie udało się obliczyć analizy topical_systemic."
            )

        if result.topical_included_cases == 0:
            return QLabel(
                "Brak przypadków z prawidłowym kodem topical_systemic do analizy."
            )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            QLabel(
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
            return QLabel(
                result.error_message
                or "Nie udało się obliczyć skuteczności leczenia wrzodów."
            )

        ulcer_success = result.ulcer_success
        if ulcer_success.eligible_cases == 0:
            return QLabel(
                "Brak przypadków wrzodowych (type_of_ulcer inne niż x i xxx) "
                "do oceny skuteczności leczenia."
            )

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Metryka", "Wartość"])
        table.setRowCount(5)
        _configure_reference_table(table)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

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

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            QLabel(
                "Skuteczność liczona tylko dla prawdziwych kategorii wrzodu "
                "(s, e, p, n, m, sceed). Wiersze z how_ended = continuation "
                "są wykluczone ze statystyki skuteczności."
            )
        )
        layout.addWidget(table)
        return container
