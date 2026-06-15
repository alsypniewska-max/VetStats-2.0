from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.patient_history import PatientHistoryDetail

PLACEHOLDER_TEXT = (
    "Wybierz pacjenta z listy po lewej stronie, aby zobaczyć jego indywidualną "
    "historię z tabel patient, clinical i micro."
)


def _configure_reference_table(table: QTableWidget) -> None:
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.horizontalHeader().setSortIndicatorShown(False)


def _build_data_table(
    columns: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    *,
    empty_message: str,
) -> QWidget:
    if not rows:
        return QLabel(empty_message)

    table = QTableWidget()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(list(columns))
    table.setRowCount(len(rows))
    _configure_reference_table(table)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    for row_index, row_values in enumerate(rows):
        for column_index, value in enumerate(row_values):
            table.setItem(row_index, column_index, QTableWidgetItem(value))

    return table


class PatientDetailsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._content_layout = QVBoxLayout()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

        content_widget = QWidget()
        content_widget.setLayout(self._content_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)

    def show_placeholder(self) -> None:
        self._clear_content()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

    def show_load_error(self, message: str) -> None:
        self._clear_content()
        self._content_layout.addWidget(
            QLabel(
                message
                or "Nie udało się wczytać danych historii pacjenta."
            )
        )

    def show_detail(self, detail: PatientHistoryDetail) -> None:
        self._clear_content()

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            QLabel(
                "Indywidualna historia pacjenta połączona po patient_ID z tabel "
                "patient, clinical i micro."
            )
        )
        summary_layout.addWidget(QLabel(detail.summary))
        self._content_layout.addWidget(summary_group)

        patient_group = QGroupBox("Dane pacjenta")
        patient_layout = QVBoxLayout(patient_group)
        for field in detail.patient_fields:
            patient_layout.addWidget(
                QLabel(f"{field.label}: {field.value}")
            )
        self._content_layout.addWidget(patient_group)

        clinical_group = QGroupBox("Powiązane wiersze clinical")
        clinical_layout = QVBoxLayout(clinical_group)
        clinical_layout.addWidget(
            _build_data_table(
                detail.clinical_columns,
                detail.clinical_rows,
                empty_message="Brak powiązanych wierszy clinical dla tego patient_ID.",
            )
        )
        self._content_layout.addWidget(clinical_group)

        micro_group = QGroupBox("Powiązane wiersze micro")
        micro_layout = QVBoxLayout(micro_group)
        micro_layout.addWidget(
            _build_data_table(
                detail.micro_columns,
                detail.micro_rows,
                empty_message="Brak powiązanych wierszy micro dla tego patient_ID.",
            )
        )
        self._content_layout.addWidget(micro_group)

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
