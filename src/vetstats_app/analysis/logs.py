from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from data_sterilizer.config import CSV_DELIMITER
from vetstats_app.analysis.report_models import AnalysisSectionReport, ReportTableBlock

LOG_ENTRY_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")

TEXT_LOG_LINE_PATTERN = re.compile(
    r"^(?:\[)?(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}|"
    r"\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})(?:\])?\s+"
    r"(?:\[(?P<level>DEBUG|INFO|WARNING|ERROR)\]|(?P<level_plain>DEBUG|INFO|WARNING|ERROR))\s+"
    r"(?:\[(?P<source>[^\]]+)\]|(?P<source_plain>\S+))\s*"
    r"(?P<message>.+)$",
    re.IGNORECASE,
)

CSV_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "time", "date", "datetime", "data", "godzina"),
    "level": ("level", "typ", "type", "severity"),
    "source": ("source", "module", "logger", "origin"),
    "message": ("message", "msg", "text", "wiadomość", "wiadomosc"),
}


@dataclass(frozen=True)
class LogEntry:
    id: str
    timestamp: str
    level: str
    source: str
    message: str


@dataclass(frozen=True)
class LogsCatalog:
    entries: tuple[LogEntry, ...]
    source_labels: tuple[str, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _normalize_level(value: object) -> str:
    text = str(value).strip().upper()
    if text in LOG_ENTRY_LEVELS:
        return text
    return "INFO"


def _resolve_csv_column(frame: pd.DataFrame, field_name: str) -> str | None:
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    for alias in CSV_COLUMN_ALIASES[field_name]:
        if alias in lower_to_actual:
            return lower_to_actual[alias]
    return None


def _parse_text_log_file(path: Path) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = TEXT_LOG_LINE_PATTERN.match(line)
        if match is None:
            rows.append(
                (
                    "",
                    "INFO",
                    path.name,
                    f"[linia {line_number}] {line}",
                )
            )
            continue

        timestamp = match.group("timestamp")
        level = match.group("level") or match.group("level_plain")
        source = match.group("source") or match.group("source_plain")
        message = match.group("message")
        rows.append((timestamp, _normalize_level(level), source, message))

    return rows


def _parse_csv_log_file(path: Path) -> list[tuple[str, str, str, str]]:
    frame = pd.read_csv(
        path,
        sep=CSV_DELIMITER,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )
    frame.columns = [str(column).strip().lstrip("\ufeff") for column in frame.columns]

    timestamp_col = _resolve_csv_column(frame, "timestamp")
    level_col = _resolve_csv_column(frame, "level")
    source_col = _resolve_csv_column(frame, "source")
    message_col = _resolve_csv_column(frame, "message")

    if message_col is None:
        raise ValueError(f"Brak kolumny message w pliku CSV: {path.name}")

    rows: list[tuple[str, str, str, str]] = []
    for _, row in frame.iterrows():
        timestamp = str(row[timestamp_col]).strip() if timestamp_col else ""
        level = _normalize_level(row[level_col]) if level_col else "INFO"
        source = str(row[source_col]).strip() if source_col else path.stem
        message = str(row[message_col]).strip()
        if not message:
            continue
        rows.append((timestamp, level, source, message))

    return rows


def _parse_log_file(path: Path) -> list[tuple[str, str, str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _parse_csv_log_file(path)
    if suffix in {".log", ".txt"}:
        return _parse_text_log_file(path)
    raise ValueError(f"Nieobsługiwany format pliku logów: {path.name}")


def build_logs_catalog(*source_paths: Path) -> LogsCatalog:
    if not source_paths:
        return LogsCatalog(
            entries=(),
            source_labels=(),
            error_message="Nie znaleziono plików logów do wczytania.",
        )

    parsed_rows: list[tuple[str, str, str, str, str]] = []
    source_labels: list[str] = []
    errors: list[str] = []

    for path in source_paths:
        if not path.is_file():
            errors.append(f"Plik nie istnieje: {path.name}")
            continue

        try:
            rows = _parse_log_file(path)
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        source_labels.append(path.name)
        for timestamp, level, source, message in rows:
            parsed_rows.append((timestamp, level, source, message, path.name))

    if errors and not parsed_rows:
        return LogsCatalog(
            entries=(),
            source_labels=tuple(source_labels),
            error_message="Nie udało się wczytać logów: " + "; ".join(errors),
        )

    parsed_rows.sort(key=lambda row: (row[0], row[4], row[3]))

    entries = tuple(
        LogEntry(
            id=f"log-{index}",
            timestamp=timestamp,
            level=level,
            source=source,
            message=message,
        )
        for index, (timestamp, level, source, message, _source_name) in enumerate(
            parsed_rows,
            start=1,
        )
    )

    error_message = None
    if errors:
        error_message = "Część plików logów nie została wczytana: " + "; ".join(errors)

    return LogsCatalog(
        entries=entries,
        source_labels=tuple(source_labels),
        error_message=error_message,
    )


def format_export_timestamp(when: datetime | None = None) -> str:
    moment = when or datetime.now()
    return moment.strftime("%d.%m.%Y %H:%M:%S")


def build_logs_section_report(
    entries: tuple[LogEntry, ...],
    *,
    source_labels: tuple[str, ...] = (),
    exported_at: datetime | None = None,
) -> AnalysisSectionReport:
    exported_at_text = format_export_timestamp(exported_at)
    summary = (
        f"Data i godzina eksportu: {exported_at_text}. "
        f"Liczba wpisów: {len(entries)}."
    )
    if source_labels:
        summary += f" Źródła plików logów: {', '.join(source_labels)}."

    return AnalysisSectionReport(
        section_title="Raport logów VetStats 2.0",
        source_labels=source_labels,
        summary_details=summary,
        interpretation_summary="Pełna historia zdarzeń aplikacji VetStats 2.0.",
        table_blocks=(
            ReportTableBlock(
                title="Historia logów",
                columns=("timestamp", "level", "source", "message"),
                rows=tuple(
                    (entry.timestamp, entry.level, entry.source, entry.message)
                    for entry in entries
                ),
            ),
        ),
    )


def write_logs_csv(
    entries: tuple[LogEntry, ...],
    destination: Path,
    *,
    exported_at: datetime | None = None,
) -> None:
    exported_at_text = format_export_timestamp(exported_at)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=CSV_DELIMITER)
        writer.writerow(["Data i godzina eksportu", exported_at_text])
        writer.writerow(["Liczba wpisów", str(len(entries))])
        writer.writerow([])
        writer.writerow(["timestamp", "level", "source", "message"])
        for entry in entries:
            writer.writerow([entry.timestamp, entry.level, entry.source, entry.message])
