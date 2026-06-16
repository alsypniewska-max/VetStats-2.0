from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import PROJECT_ROOT
from vetstats_app.analysis.logs import (
    LogEntry,
    LogsCatalog,
    build_logs_catalog,
    write_logs_csv,
    write_logs_report,
)

VETSTATS_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
PROJECT_LOGS_DIR = PROJECT_ROOT / "logs"


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

    def get_load_error(self) -> str | None:
        return self._load_error

    def get_detail(self, entry_id: str) -> LogEntry | None:
        if self._load_error is not None and not self._entries_by_id:
            return None
        return self._entries_by_id.get(entry_id)

    def get_all_entries(self) -> tuple[LogEntry, ...]:
        catalog = self.load_catalog()
        return catalog.entries

    def export_report(self, destination: Path) -> str | None:
        entries = self.get_all_entries()
        if not entries:
            return "Brak wpisów logów do wyeksportowania."
        try:
            write_logs_report(entries, destination)
        except OSError as exc:
            return f"Nie udało się zapisać raportu logów: {exc}"
        return None

    def export_csv(self, destination: Path) -> str | None:
        entries = self.get_all_entries()
        if not entries:
            return "Brak wpisów logów do wyeksportowania."
        try:
            write_logs_csv(entries, destination)
        except OSError as exc:
            return f"Nie udało się zapisać pliku CSV: {exc}"
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

    def _resolve_source_paths(self) -> tuple[Path, ...]:
        if self._logs_dir is not None:
            return self._collect_log_files(self._logs_dir)

        primary_dir = VETSTATS_LOGS_DIR
        primary_files = self._collect_log_files(primary_dir)
        if primary_files:
            return primary_files

        if PROJECT_LOGS_DIR.is_dir():
            return self._collect_log_files(PROJECT_LOGS_DIR)

        return ()

    @staticmethod
    def _collect_log_files(directory: Path) -> tuple[Path, ...]:
        if not directory.is_dir():
            return ()

        preferred = (
            directory / "app.log",
            directory / "app.csv",
        )
        paths: list[Path] = [path for path in preferred if path.is_file()]

        if paths:
            return tuple(paths)

        discovered = sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".log", ".csv", ".txt"}
        )
        return tuple(discovered)
