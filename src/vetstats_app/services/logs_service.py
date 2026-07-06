from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from vetstats_app.analysis.logs import (
    LogEntry,
    LogsCatalog,
    build_detailed_analysis_context_block,
    build_logs_catalog,
    build_logs_section_report,
    write_logs_csv,
)
from vetstats_app.analysis.detailed_comparative_analysis import (
    format_detailed_analysis_settings_lines,
)
from vetstats_app.services.app_event_logger import APP_LOG_FILE, log_error, log_info
from vetstats_app.services.full_report_service import DetailedAnalysisContext
from vetstats_app.services.section_report_pdf import write_section_report_pdf


class LogsService:
    def __init__(
        self,
        logs_dir: Path | None = None,
        *,
        detailed_context_provider: Callable[[], DetailedAnalysisContext] | None = None,
    ) -> None:
        self._logs_dir = logs_dir
        self._detailed_context_provider = detailed_context_provider
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
        context_lines = self._detailed_analysis_context_lines()
        context_blocks = ()
        if context_lines:
            context_blocks = (build_detailed_analysis_context_block(context_lines),)
        report = build_logs_section_report(
            entries,
            source_labels=tuple(self._source_labels()),
            exported_at=exported_at,
            context_blocks=context_blocks,
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
        context_lines = self._detailed_analysis_context_lines()
        try:
            write_logs_csv(
                entries,
                destination,
                exported_at=exported_at,
                context_lines=context_lines,
            )
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

    def _detailed_analysis_context_lines(self) -> tuple[str, ...]:
        if self._detailed_context_provider is None:
            return ()
        context = self._detailed_context_provider()
        lines = list(format_detailed_analysis_settings_lines(context.state))
        if context.last_result is not None and context.last_result.is_success:
            lines.append(
                "Ostatnia analiza: zakończona pomyślnie "
                f"({context.last_result.variable_label})."
            )
        elif context.last_result is not None:
            lines.append("Ostatnia analiza: nie powiodła się.")
        return tuple(lines)
