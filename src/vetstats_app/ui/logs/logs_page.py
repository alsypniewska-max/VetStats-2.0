from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QFileDialog, QMessageBox, QWidget

from vetstats_app.services.logs_service import LogsService
from vetstats_app.ui.logs.logs_detail_panel import LogsDetailPanel
from vetstats_app.ui.logs.logs_list_panel import LogsListPanel


class LogsSection(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._service = LogsService()
        self._logs_list_panel = LogsListPanel()
        self._logs_detail_panel = LogsDetailPanel()

        catalog = self._service.load_catalog()
        self._logs_list_panel.populate(catalog)

        layout = QHBoxLayout(self)
        layout.addWidget(self._logs_list_panel)
        layout.addWidget(self._logs_detail_panel, stretch=1)

        self._logs_list_panel.connect_current_log_entry_changed(
            self._on_log_entry_selected
        )
        self._logs_detail_panel.connect_generate_report(self._on_generate_report)
        self._logs_detail_panel.connect_export_csv(self._on_export_csv)

        self._logs_list_panel.clear_selection()
        has_entries = bool(catalog.entries)
        self._logs_detail_panel.set_export_enabled(has_entries)

        if self._service.get_load_error() is not None and not has_entries:
            self._logs_detail_panel.show_load_error(
                self._service.get_load_error()
                or catalog.error_message
                or "Nie udało się wczytać logów."
            )
        else:
            self._logs_detail_panel.show_placeholder()

    def _on_log_entry_selected(self, entry_id: str | None) -> None:
        load_error = self._service.get_load_error()
        if load_error is not None and not self._service.get_all_entries():
            self._logs_detail_panel.show_load_error(load_error)
            return

        if entry_id is None:
            self._logs_detail_panel.show_placeholder()
            return

        entry = self._service.get_detail(entry_id)
        if entry is None:
            self._logs_detail_panel.show_placeholder()
            return

        self._logs_detail_panel.show_detail(entry)

    def _on_generate_report(self) -> None:
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Generate Logs Report",
            "logs_report.txt",
            "Pliki tekstowe (*.txt);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._service.export_report(Path(destination))
        if error_message is not None:
            QMessageBox.warning(self, "Generate Logs Report", error_message)
            return

        self._logs_detail_panel.show_status_message(
            f"Zapisano raport logów: {destination}"
        )

    def _on_export_csv(self) -> None:
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Logs as CSV",
            "logs_export.csv",
            "Pliki CSV (*.csv);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._service.export_csv(Path(destination))
        if error_message is not None:
            QMessageBox.warning(self, "Export Logs as CSV", error_message)
            return

        self._logs_detail_panel.show_status_message(
            f"Zapisano logi jako CSV: {destination}"
        )
