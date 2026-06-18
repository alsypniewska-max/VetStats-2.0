from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.logs import LogEntry

PLACEHOLDER_TEXT = (
    "Wybierz wpis logu z listy po lewej stronie, aby zobaczyć jego szczegóły."
)


def _detail_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class LogsDetailPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._content_layout = QVBoxLayout()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

        content_widget = QWidget()
        content_widget.setLayout(self._content_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        self._export_pdf_button = QPushButton("Eksportuj logi do PDF")
        self._export_csv_button = QPushButton("Eksportuj logi do CSV")

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self._export_pdf_button)
        controls_layout.addWidget(self._export_csv_button)
        controls_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area, stretch=1)
        layout.addLayout(controls_layout)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    def connect_export_pdf(self, callback: Callable[[], None]) -> None:
        self._export_pdf_button.clicked.connect(callback)

    def connect_export_csv(self, callback: Callable[[], None]) -> None:
        self._export_csv_button.clicked.connect(callback)

    def set_export_enabled(self, enabled: bool) -> None:
        self._export_pdf_button.setEnabled(enabled)
        self._export_csv_button.setEnabled(enabled)

    def show_status_message(self, message: str) -> None:
        self._status_label.setText(message)

    def show_placeholder(self) -> None:
        self._clear_content()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

    def show_load_error(self, message: str) -> None:
        self._clear_content()
        self._content_layout.addWidget(
            _detail_label(message or "Nie udało się wczytać logów.")
        )

    def show_detail(self, entry: LogEntry) -> None:
        self._clear_content()

        detail_group = QGroupBox("Szczegóły wpisu logu")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(_detail_label(f"ID: {entry.id}"))
        detail_layout.addWidget(
            _detail_label(f"Czas: {entry.timestamp or '—'}")
        )
        detail_layout.addWidget(_detail_label(f"Poziom: {entry.level}"))
        detail_layout.addWidget(_detail_label(f"Źródło: {entry.source or '—'}"))
        detail_layout.addWidget(_detail_label(f"Wiadomość: {entry.message}"))
        self._content_layout.addWidget(detail_group)

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
