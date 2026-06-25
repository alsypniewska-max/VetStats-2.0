"""Schema definition for patient.csv."""

from __future__ import annotations

import re
from datetime import datetime

DATASET_NAME = "patient"

REQUIRED_COLUMNS: tuple[str, ...] = (
    "patient_ID",
    "name",
    "date_of_birth",
    "species",
    "breed",
    "gender",
    "diseases_not_opht",
    "other_diseases_opht",
)

TEXT_COLUMNS: tuple[str, ...] = REQUIRED_COLUMNS
DATE_OF_BIRTH_COLUMN = "date_of_birth"
GENDER_COLUMN = "gender"
PATIENT_ID_COLUMN = "patient_ID"
DISEASES_NOT_OPHT_COLUMN = "diseases_not_opht"
OTHER_DISEASES_OPHT_COLUMN = "other_diseases_opht"

OTHER_DISEASES_OPHT_TOKEN_TYPOS: dict[str, str] = {
    "didtihiasis": "distichiasis",
}

DATE_PATTERN = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
ALLOWED_GENDERS = frozenset({"m", "f"})
EMPTY_VALUE_REPLACEMENT = "xxx"


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


def is_valid_date_of_birth(value: str) -> bool:
    """Return True when ``value`` is a valid date in d.m.yyyy or dd.mm.yyyy format."""
    if not DATE_PATTERN.match(value):
        return False

    day_text, month_text, year_text = value.split(".")
    try:
        datetime(int(year_text), int(month_text), int(day_text))
    except ValueError:
        return False
    return True


def is_trailing_empty_column(column_name: str) -> bool:
    """Return True for pandas placeholder columns created by trailing delimiters."""
    return str(column_name).startswith("Unnamed:")


def normalize_other_diseases_opht_tokens(value: str) -> str:
    """Fix known token typos in semicolon-separated ophthalmic disease values."""
    stripped = str(value).strip().lower()
    if not stripped:
        return stripped

    if ";" not in stripped:
        return OTHER_DISEASES_OPHT_TOKEN_TYPOS.get(stripped, stripped)

    tokens = [token.strip() for token in stripped.split(";")]
    corrected = [OTHER_DISEASES_OPHT_TOKEN_TYPOS.get(token, token) for token in tokens]
    return ";".join(corrected)
