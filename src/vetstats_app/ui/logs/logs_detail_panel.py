from collections.abc import Callable

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

        self._generate_report_button = QPushButton("Generate Logs Report")
        self._export_csv_button = QPushButton("Export Logs as CSV")

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self._generate_report_button)
        controls_layout.addWidget(self._export_csv_button)
        controls_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area, stretch=1)
        layout.addLayout(controls_layout)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

    def connect_generate_report(self, callback: Callable[[], None]) -> None:
        self._generate_report_button.clicked.connect(callback)

    def connect_export_csv(self, callback: Callable[[], None]) -> None:
        self._export_csv_button.clicked.connect(callback)

    def set_export_enabled(self, enabled: bool) -> None:
        self._generate_report_button.setEnabled(enabled)
        self._export_csv_button.setEnabled(enabled)

    def show_status_message(self, message: str) -> None:
        self._status_label.setText(message)

    def show_placeholder(self) -> None:
        self._clear_content()
        self._content_layout.addWidget(QLabel(PLACEHOLDER_TEXT))

    def show_load_error(self, message: str) -> None:
        self._clear_content()
        self._content_layout.addWidget(
            QLabel(message or "Nie udało się wczytać logów.")
        )

    def show_detail(self, entry: LogEntry) -> None:
        self._clear_content()

        detail_group = QGroupBox("Szczegóły wpisu logu")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(QLabel(f"ID: {entry.id}"))
        detail_layout.addWidget(QLabel(f"Timestamp: {entry.timestamp or '—'}"))
        detail_layout.addWidget(QLabel(f"Level: {entry.level}"))
        detail_layout.addWidget(QLabel(f"Source: {entry.source or '—'}"))
        detail_layout.addWidget(QLabel(f"Message: {entry.message}"))
        self._content_layout.addWidget(detail_group)

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
