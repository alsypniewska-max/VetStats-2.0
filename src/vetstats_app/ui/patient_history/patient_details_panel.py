from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.patient_history import PatientHistoryDetail
from vetstats_app.services.patient_history_service import PatientHistoryService

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


class _AutoResizeTable(QTableWidget):
    """Reference table that wraps cell text and grows its rows/height to fit it.

    Column widths are bounded to the viewport (stretch), so long values wrap onto
    multiple lines instead of staying on one horizontal line. Row heights and the
    overall fixed height are recomputed whenever the real width becomes known.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def showEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        super().showEvent(event)
        self._adjust_height()

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        super().resizeEvent(event)
        self._adjust_height()

    def _adjust_height(self) -> None:
        self.resizeRowsToContents()
        height = (
            self.horizontalHeader().height()
            + self.verticalHeader().length()
            + 2 * self.frameWidth()
            + 2
        )
        if self.height() != height:
            self.setFixedHeight(height)


def _build_data_table(
    columns: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    *,
    empty_message: str,
) -> QWidget:
    if not rows:
        label = QLabel(empty_message)
        label.setWordWrap(True)
        return label

    table = _AutoResizeTable()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(list(columns))
    table.setRowCount(len(rows))
    _configure_reference_table(table)

    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    header.setMinimumSectionSize(40)

    for row_index, row_values in enumerate(rows):
        for column_index, value in enumerate(row_values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            table.setItem(row_index, column_index, item)

    table.resizeRowsToContents()
    return table


def _build_summary_label(lines: tuple[str, ...], *, empty_message: str) -> QLabel:
    text = "\n".join(lines) if lines else empty_message
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    label.setMinimumWidth(0)
    return label


class PatientDetailsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._current_detail: PatientHistoryDetail | None = None
        self._service: PatientHistoryService | None = None

        self._export_button = QPushButton("Eksportuj historię pacjenta do PDF")
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(self._on_export_pdf)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self._export_button)
        top_bar.addStretch()

        self._content_layout = QVBoxLayout()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

        content_widget = QWidget()
        content_widget.setLayout(self._content_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addLayout(top_bar)
        layout.addWidget(scroll_area, stretch=1)

    def show_placeholder(self) -> None:
        self._current_detail = None
        self._export_button.setEnabled(False)
        self._clear_content()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

    def show_load_error(self, message: str) -> None:
        self._current_detail = None
        self._export_button.setEnabled(False)
        self._clear_content()
        self._content_layout.addWidget(
            QLabel(
                message
                or "Nie udało się wczytać danych historii pacjenta."
            )
        )

    def show_detail(self, detail: PatientHistoryDetail) -> None:
        self._current_detail = detail
        self._export_button.setEnabled(True)
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
            field_label = QLabel(f"{field.label}: {field.value}")
            field_label.setWordWrap(True)
            field_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            patient_layout.addWidget(field_label)
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

        clinical_summary_group = QGroupBox("Podsumowanie clinical")
        clinical_summary_layout = QVBoxLayout(clinical_summary_group)
        clinical_summary_layout.addWidget(
            _build_summary_label(
                detail.clinical_summary_lines,
                empty_message="Brak danych clinical do podsumowania.",
            )
        )
        self._content_layout.addWidget(clinical_summary_group)

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

        micro_summary_group = QGroupBox("Podsumowanie micro")
        micro_summary_layout = QVBoxLayout(micro_summary_group)
        micro_summary_layout.addWidget(
            _build_summary_label(
                detail.micro_summary_lines,
                empty_message="Brak danych micro do podsumowania.",
            )
        )
        self._content_layout.addWidget(micro_summary_group)

    def _on_export_pdf(self) -> None:
        if self._current_detail is None:
            QMessageBox.information(
                self,
                "Eksportuj historię pacjenta do PDF",
                "Najpierw wybierz pacjenta z listy.",
            )
            return

        default_name = f"historia_pacjenta_{self._current_detail.patient_id}.pdf"
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Eksportuj historię pacjenta do PDF",
            default_name,
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        if self._service is None:
            self._service = PatientHistoryService()

        error_message = self._service.export_patient_history_pdf(
            self._current_detail,
            Path(destination),
        )
        if error_message is not None:
            QMessageBox.warning(
                self,
                "Eksportuj historię pacjenta do PDF",
                error_message,
            )
            return

        QMessageBox.information(
            self,
            "Eksportuj historię pacjenta do PDF",
            f"Zapisano historię pacjenta do pliku:\n{destination}",
        )

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
