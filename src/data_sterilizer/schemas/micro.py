"""Schema definition for micro.csv."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

DATASET_NAME = "micro"

BASE_COLUMNS: tuple[str, ...] = (
    "patient_ID",
    "result_ID",
    "date_result",
    "date_received",
    "date_collect",
    "bacteria",
    "growth",
)

ANTIBIOTIC_COLUMNS: tuple[str, ...] = (
    "amikacin",
    "amoxy/clavulanic",
    "azithromycin",
    "Cephalexin",
    "Ceftriaxon",
    "Ciprofloxacin",
    "Chloramfenicol",
    "Doxycycline",
    "Enrofloxacin",
    "Erythromycin",
    "Gentamycin",
    "Marbofloxacin",
    "Moxifloxacin",
    "Neomycin",
    "Ofloxacin",
    "Tobramycin",
)

REQUIRED_COLUMNS: tuple[str, ...] = BASE_COLUMNS + ANTIBIOTIC_COLUMNS
TEXT_COLUMNS: tuple[str, ...] = REQUIRED_COLUMNS

PATIENT_ID_COLUMN = "patient_ID"
RESULT_ID_COLUMN = "result_ID"
DATE_RESULT_COLUMN = "date_result"
DATE_RECEIVED_COLUMN = "date_received"
DATE_COLLECT_COLUMN = "date_collect"
BACTERIA_COLUMN = "bacteria"
GROWTH_COLUMN = "growth"

DATE_COLUMNS: tuple[str, ...] = (
    DATE_RESULT_COLUMN,
    DATE_RECEIVED_COLUMN,
    DATE_COLLECT_COLUMN,
)

SUSCEPTIBILITY_COLUMNS: tuple[str, ...] = (GROWTH_COLUMN,) + ANTIBIOTIC_COLUMNS
GLOBAL_EMPTY_COLUMNS: tuple[str, ...] = (
    PATIENT_ID_COLUMN,
    RESULT_ID_COLUMN,
    DATE_RESULT_COLUMN,
    DATE_RECEIVED_COLUMN,
    DATE_COLLECT_COLUMN,
    BACTERIA_COLUMN,
)

DATE_PATTERN = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
RESULT_ID_YEAR_PATTERN = re.compile(r"^\d+/(\d{4})$")
ALLOWED_GROWTH = frozenset({"heavy", "scant", "x"})
ALLOWED_SUSCEPTIBILITY = frozenset({"+++", "+", "0", "x"})
ALLOWED_POSITIVE_SUSCEPTIBILITY = frozenset({"+++", "+", "0"})
NEGATIVE_BACTERIA_VALUE = "negative"
NOT_APPLICABLE_VALUE = "x"
EMPTY_VALUE_REPLACEMENT = "xxx"
DUPLICATE_KEY_COLUMNS: tuple[str, ...] = (PATIENT_ID_COLUMN, RESULT_ID_COLUMN, BACTERIA_COLUMN)


def normalize_column_names(columns: list[str]) -> dict[str, str]:
    """Map actual column names to canonical names using case-insensitive matching."""
    rename_map: dict[str, str] = {}
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in columns
    }

    for canonical in REQUIRED_COLUMNS:
        actual = lower_to_actual.get(canonical.lower())
        if actual is not None and actual != canonical:
            rename_map[actual] = canonical

    return rename_map


def is_trailing_empty_column(column_name: str) -> bool:
    return str(column_name).startswith("Unnamed:")


def is_valid_micro_date(value: str) -> bool:
    if not DATE_PATTERN.match(value):
        return False

    day_text, month_text, year_text = value.split(".")
    try:
        datetime(int(year_text), int(month_text), int(day_text))
    except ValueError:
        return False
    return True


def parse_micro_date(value: str) -> datetime | None:
    if not is_valid_micro_date(value):
        return None
    day_text, month_text, year_text = value.split(".")
    return datetime(int(year_text), int(month_text), int(day_text))


def format_micro_date(value: datetime) -> str:
    return f"{value.day}.{value.month}.{value.year}"


def parse_result_id_year(result_id: str) -> int | None:
    """Extract the 4-digit year suffix from result_ID values such as 003/2025."""
    match = RESULT_ID_YEAR_PATTERN.match(str(result_id).strip())
    if match is None:
        return None
    return int(match.group(1))


def replace_micro_date_year(date_value: str, year: int) -> str | None:
    """Replace only the year in a valid micro date string."""
    if not is_valid_micro_date(date_value):
        return None
    day_text, month_text, _year_text = date_value.split(".")
    return f"{day_text}.{month_text}.{year}"


def subtract_one_day(value: str) -> str | None:
    parsed = parse_micro_date(value)
    if parsed is None:
        return None
    return format_micro_date(parsed - timedelta(days=1))


def is_missing_date_collect(value: str) -> bool:
    stripped = str(value).strip().lower()
    return stripped == "" or stripped == EMPTY_VALUE_REPLACEMENT
