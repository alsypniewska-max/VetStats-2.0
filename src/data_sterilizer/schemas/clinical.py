"""Schema definition for clinical.csv."""

from __future__ import annotations

import re
from datetime import datetime

DATASET_NAME = "clinical"

HOW_ENDED_COLUMN = "how_ended"
DATE_LAST_APPOINTMENT_COLUMN = "date_last_appointment"

REQUIRED_COLUMNS: tuple[str, ...] = (
    "patient_ID",
    "eye",
    "type_of_ulcer",
    "date_appointment_first_before_micro",
    "duration_of_problem",
    "drug_used_before_micro",
    "farmacology_surgery",
    "topical_systemic",
    "EMS",
    "type_of_surgery",
    "top_treatment_after",
    "sys_treatment_after",
    "how_ended",
)

OPTIONAL_COLUMNS: tuple[str, ...] = (DATE_LAST_APPOINTMENT_COLUMN,)
CANONICAL_COLUMNS: tuple[str, ...] = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

TEXT_COLUMNS: tuple[str, ...] = REQUIRED_COLUMNS

PATIENT_ID_COLUMN = "patient_ID"
EYE_COLUMN = "eye"
TYPE_OF_ULCER_COLUMN = "type_of_ulcer"
DATE_APPOINTMENT_COLUMN = "date_appointment_first_before_micro"
DURATION_COLUMN = "duration_of_problem"
DRUG_BEFORE_MICRO_COLUMN = "drug_used_before_micro"
FARMACOLOGY_SURGERY_COLUMN = "farmacology_surgery"
TOPICAL_SYSTEMIC_COLUMN = "topical_systemic"
EMS_COLUMN = "EMS"
TYPE_OF_SURGERY_COLUMN = "type_of_surgery"
TOP_TREATMENT_COLUMN = "top_treatment_after"
SYS_TREATMENT_COLUMN = "sys_treatment_after"

DATE_PATTERN = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
DURATION_PATTERN = re.compile(
    r"^(?P<number>\d+(?:[.,]\d+)?)\s+(?P<unit>day|days|week|weeks|month|months|year|years)$"
)

ALLOWED_EYES = frozenset({"r", "l", "b", "xxx"})
ALLOWED_ULCER_TYPES = frozenset({"s", "e", "p", "m", "n", "sceed", "x"})
ALLOWED_FARMACOLOGY = frozenset({"f", "s", "xxx"})
ALLOWED_TOPICAL_SYSTEMIC = frozenset({"t", "s", "ts"})
ALLOWED_EMS = frozenset({"yes", "no", "xxx"})
TYPE_OF_SURGERY_CODE_ORDER: tuple[str, ...] = (
    "3deb",
    "deb",
    "debkol",
    "kol",
    "psu",
    "psuk",
    "ps",
    "pk",
    "resection",
)
TYPE_OF_SURGERY_SHORT_LABELS: dict[str, str] = {
    "3deb": "3DEB",
    "deb": "deb",
    "debkol": "debkol",
    "kol": "kol",
    "psu": "PSU",
    "psuk": "PSUK",
    "ps": "PS",
    "pk": "PK",
    "resection": "resection",
}
TYPE_OF_SURGERY_DISPLAY_LABELS: dict[str, str] = {
    "3deb": "Debridement + opatrunek z trzeciej powieki",
    "deb": "debridement",
    "debkol": "debridement + soczewka kolagenowa",
    "kol": "soczewka kolagenowa",
    "psu": "Przeszczep spojówkowy uszypułowany",
    "psuk": "Przeszczep spojówkowy uszypułowany + kolagenowy",
    "ps": "Przeszczep spojówkowy wyspowy",
    "pk": "Przeszczep kolagenowy",
    "resection": "Resekcja (martwaka)",
}
ALLOWED_SURGERY_TYPES = frozenset(TYPE_OF_SURGERY_DISPLAY_LABELS)
ALLOWED_DRUG_SENTINELS = frozenset({"x", "xxx"})
ALLOWED_HOW_ENDED = frozenset({"good", "no followup", "enucleation", "continuation", "xxx"})
HOW_ENDED_REQUIRES_X_DATE_LAST = frozenset({"no followup", "continuation"})
EMPTY_VALUE_REPLACEMENT = "xxx"
UNKNOWN_VALUE = "xxx"
NOT_APPLICABLE_VALUE = "x"

DURATION_UNIT_TYPO_MAP: dict[str, str] = {
    "monts": "months",
    "mont": "month",
    "weks": "weeks",
    "wek": "week",
}


def normalize_column_names(columns: list[str]) -> dict[str, str]:
    """Map actual column names to canonical names using case-insensitive matching."""
    rename_map: dict[str, str] = {}
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in columns
    }

    for canonical in CANONICAL_COLUMNS:
        actual = lower_to_actual.get(canonical.lower())
        if actual is not None and actual != canonical:
            rename_map[actual] = canonical

    return rename_map


def is_valid_clinical_date(value: str) -> bool:
    """Return True when ``value`` is a valid date in d.m.yyyy or dd.mm.yyyy format."""
    if not DATE_PATTERN.match(value):
        return False

    day_text, month_text, year_text = value.split(".")
    try:
        datetime(int(year_text), int(month_text), int(day_text))
    except ValueError:
        return False
    return True


def is_valid_duration(value: str) -> bool:
    """Return True for xxx or a float amount followed by an allowed time unit."""
    if value == UNKNOWN_VALUE:
        return True
    return DURATION_PATTERN.match(value) is not None


def normalize_duration_value(value: str) -> str:
    """Fix common unit typos in duration_of_problem values."""
    stripped = str(value).strip().lower()
    if stripped == UNKNOWN_VALUE or is_valid_duration(stripped):
        return stripped

    if " " not in stripped:
        return stripped

    number, unit = stripped.rsplit(" ", 1)
    corrected_unit = DURATION_UNIT_TYPO_MAP.get(unit, unit)
    if corrected_unit == unit:
        return stripped
    return f"{number} {corrected_unit}"


def parse_clinical_date(value: str):
    """Return a datetime for a valid clinical date string, else None."""
    if not is_valid_clinical_date(value):
        return None
    day_text, month_text, year_text = value.split(".")
    return datetime(int(year_text), int(month_text), int(day_text))


def is_trailing_empty_column(column_name: str) -> bool:
    return str(column_name).startswith("Unnamed:")
