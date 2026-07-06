from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from vetstats_app.services.full_report_service import DetailedAnalysisContext
from vetstats_app.services.logs_service import LogsService
from vetstats_app.ui.logs.logs_context_panel import LogsContextPanel
from vetstats_app.ui.logs.logs_detail_panel import LogsDetailPanel
from vetstats_app.ui.logs.logs_list_panel import LogsListPanel


class LogsSection(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        detailed_context_provider: Callable[[], DetailedAnalysisContext] | None = None,
    ) -> None:
        super().__init__(parent)

        self._service = LogsService(
            detailed_context_provider=detailed_context_provider,
        )
        self._context_panel = LogsContextPanel()
        self._context_panel.set_context_provider(detailed_context_provider)
        self._logs_list_panel = LogsListPanel()
        self._logs_detail_panel = LogsDetailPanel()

        body_layout = QHBoxLayout()
        body_layout.addWidget(self._logs_list_panel)
        body_layout.addWidget(self._logs_detail_panel, stretch=1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._context_panel)
        layout.addLayout(body_layout, stretch=1)

        self._logs_list_panel.connect_current_log_entry_changed(
            self._on_log_entry_selected
        )
        self._logs_detail_panel.connect_export_pdf(self._on_export_pdf)
        self._logs_detail_panel.connect_export_csv(self._on_export_csv)

        self._reload_logs_view(clear_selection=True)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._reload_logs_view(clear_selection=False)

    def _reload_logs_view(self, *, clear_selection: bool) -> None:
        self._context_panel.refresh()
        catalog = self._service.reload_catalog()
        self._logs_list_panel.populate(catalog)

        has_entries = bool(catalog.entries)
        self._logs_detail_panel.set_export_enabled(has_entries)

        if clear_selection:
            self._logs_list_panel.clear_selection()

        load_error = self._service.get_load_error()
        if load_error is not None and not has_entries:
            self._logs_detail_panel.show_load_error(
                load_error
                or catalog.error_message
                or "Nie udało się wczytać logów."
            )
        elif not clear_selection:
            selected_entry_id = self._logs_list_panel.current_entry_id()
            if selected_entry_id:
                entry = self._service.get_detail(selected_entry_id)
                if entry is not None:
                    self._logs_detail_panel.show_detail(entry)
                    return
            self._logs_detail_panel.show_placeholder()
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

    def _on_export_pdf(self) -> None:
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Eksportuj logi do PDF",
            "logs_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._service.export_pdf(Path(destination))
        if error_message is not None:
            QMessageBox.warning(self, "Eksportuj logi do PDF", error_message)
            return

        self._reload_logs_view(clear_selection=False)
        self._logs_detail_panel.show_status_message(
            f"Zapisano raport logów do PDF: {destination}"
        )

    def _on_export_csv(self) -> None:
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Eksportuj logi do CSV",
            "logs_export.csv",
            "Pliki CSV (*.csv);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return

        error_message = self._service.export_csv(Path(destination))
        if error_message is not None:
            QMessageBox.warning(self, "Eksportuj logi do CSV", error_message)
            return

        self._reload_logs_view(clear_selection=False)
        self._logs_detail_panel.show_status_message(
            f"Zapisano logi jako CSV: {destination}"
        )
