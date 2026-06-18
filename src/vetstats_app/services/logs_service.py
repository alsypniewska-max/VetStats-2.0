from __future__ import annotations

from datetime import datetime
from pathlib import Path

from vetstats_app.analysis.logs import (
    LogEntry,
    LogsCatalog,
    build_logs_catalog,
    build_logs_section_report,
    write_logs_csv,
)
from vetstats_app.services.app_event_logger import APP_LOG_FILE, log_error, log_info
from vetstats_app.services.section_report_pdf import write_section_report_pdf


class LogsService:
    def __init__(self, logs_dir: Path | None = None) -> None:
        self._logs_dir = logs_dir
        self._catalog: LogsCatalog | None = None
        self._entries_by_id: dict[str, LogEntry] = {}
        self._load_error: str | None = None
        self._source_paths: tuple[Path, ...] = ()
        self._load_catalog()

    def load_catalog(self) -> LogsCatalog:
        if self._catalog is None:
            return LogsCatalog(
                entries=(),
                source_labels=(),
                error_message=self._load_error or "Nie wczytano logów.",
            )
        return self._catalog

    def reload_catalog(self) -> LogsCatalog:
        self._load_catalog()
        return self.load_catalog()

    def get_load_error(self) -> str | None:
        return self._load_error

    def get_detail(self, entry_id: str) -> LogEntry | None:
        if self._load_error is not None and not self._entries_by_id:
            return None
        return self._entries_by_id.get(entry_id)

    def get_all_entries(self) -> tuple[LogEntry, ...]:
        catalog = self.load_catalog()
        return catalog.entries

    def export_pdf(self, destination: Path) -> str | None:
        entries = self.get_all_entries()
        if not entries:
            return "Brak wpisów logów do wyeksportowania."

        exported_at = datetime.now()
        report = build_logs_section_report(
            entries,
            source_labels=tuple(self._source_labels()),
            exported_at=exported_at,
        )
        try:
            write_section_report_pdf(report, Path(destination))
        except OSError as exc:
            message = f"Nie udało się zapisać raportu PDF logów: {exc}"
            log_error("logs", message)
            return message

        log_info(
            "logs",
            f"Eksport logów do PDF: {Path(destination).name} ({len(entries)} wpisy)",
        )
        return None

    def export_csv(self, destination: Path) -> str | None:
        entries = self.get_all_entries()
        if not entries:
            return "Brak wpisów logów do wyeksportowania."

        exported_at = datetime.now()
        try:
            write_logs_csv(entries, destination, exported_at=exported_at)
        except OSError as exc:
            message = f"Nie udało się zapisać pliku CSV: {exc}"
            log_error("logs", message)
            return message

        log_info(
            "logs",
            f"Eksport logów do CSV: {Path(destination).name} ({len(entries)} wpisy)",
        )
        return None

    def _load_catalog(self) -> None:
        self._source_paths = self._resolve_source_paths()
        catalog = build_logs_catalog(*self._source_paths)
        self._catalog = catalog
        self._entries_by_id = {entry.id: entry for entry in catalog.entries}

        if not catalog.is_success and not catalog.entries:
            self._load_error = catalog.error_message
        elif not catalog.entries:
            self._load_error = catalog.error_message or "Brak wpisów logów."
        else:
            self._load_error = None

    def _source_labels(self) -> list[str]:
        if self._source_paths:
            return [path.name for path in self._source_paths]
        if APP_LOG_FILE.is_file():
            return [APP_LOG_FILE.name]
        return []

    def _resolve_source_paths(self) -> tuple[Path, ...]:
        if self._logs_dir is not None:
            candidate = self._logs_dir / "app.log"
            return (candidate,) if candidate.is_file() else ()

        if APP_LOG_FILE.is_file():
            return (APP_LOG_FILE,)

        return ()
