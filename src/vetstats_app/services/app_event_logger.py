from __future__ import annotations

from datetime import datetime
from pathlib import Path

VETSTATS_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
APP_LOG_FILE = VETSTATS_LOGS_DIR / "app.log"


def _ensure_log_dir() -> None:
    VETSTATS_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _format_line(level: str, source: str, message: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{timestamp} {level.upper()} {source} {message}"


def log_event(level: str, source: str, message: str) -> None:
    _ensure_log_dir()
    line = _format_line(level, source, message)
    with APP_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def log_debug(source: str, message: str) -> None:
    log_event("DEBUG", source, message)


def log_info(source: str, message: str) -> None:
    log_event("INFO", source, message)


def log_warning(source: str, message: str) -> None:
    log_event("WARNING", source, message)


def log_error(source: str, message: str) -> None:
    log_event("ERROR", source, message)


def start_new_session() -> None:
    """Reset the session log file on application startup."""
    _ensure_log_dir()
    line = _format_line("INFO", "app", "Rozpoczęto nową sesję aplikacji")
    APP_LOG_FILE.write_text(line + "\n", encoding="utf-8")
