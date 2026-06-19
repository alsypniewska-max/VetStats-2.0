from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import pandas as pd

from vetstats_app.analysis.population_characteristics import (
    CAT_SPECIES,
    DOG_SPECIES,
)
from vetstats_app.analysis.treatment_groups import REAL_ULCER_CODES

UNKNOWN_VALUE = "xxx"


def resolve_column(frame: pd.DataFrame, column_name: str) -> str | None:
    if column_name in frame.columns:
        return column_name

    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    return lower_to_actual.get(column_name.lower())


def format_display_value(value: object) -> str:
    unknown_label = "nie wiadomo"
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return unknown_label

    text = str(value).strip()
    if not text or text.lower() == UNKNOWN_VALUE:
        return unknown_label
    return text


def normalize_text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower()
    if not text or text == UNKNOWN_VALUE:
        return None
    return text


def normalize_ulcer_code(value: object) -> str | None:
    text = normalize_text(value)
    if text is None or text not in REAL_ULCER_CODES:
        return None
    return text


def is_real_ulcer_code(value: object) -> bool:
    return normalize_ulcer_code(value) is not None


def classify_species(value: object) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    if text in DOG_SPECIES:
        return "dog"
    if text in CAT_SPECIES:
        return "cat"
    return None


def normalize_breed(value: object) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    return text


def parse_clinical_dmy_date(value: object) -> date | None:
    text = format_display_value(value)
    if text == "nie wiadomo":
        return None
    parts = text.split(".")
    if len(parts) != 3:
        return None
    try:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except ValueError:
        return None


@dataclass(frozen=True)
class DurationSummaryStats:
    count: int
    mean: float | None
    median: float | None
    percentile_25: float | None
    percentile_75: float | None


@dataclass(frozen=True)
class ExtendedDurationSummaryStats:
    count: int
    mean_days: float | None
    median_days: float | None
    min_days: float | None
    max_days: float | None
    percentile_25_days: float | None
    percentile_75_days: float | None


def summarize_duration_values_extended(
    values: tuple[float, ...],
) -> ExtendedDurationSummaryStats:
    if not values:
        return ExtendedDurationSummaryStats(0, None, None, None, None, None, None)

    sorted_values = sorted(values)
    base = summarize_duration_values(values)
    return ExtendedDurationSummaryStats(
        count=base.count,
        mean_days=base.mean,
        median_days=base.median,
        min_days=sorted_values[0],
        max_days=sorted_values[-1],
        percentile_25_days=base.percentile_25,
        percentile_75_days=base.percentile_75,
    )


def build_patient_species_breed_lookup(
    patient: pd.DataFrame,
) -> dict[str, tuple[object, object]]:
    from data_sterilizer.schemas.patient import PATIENT_ID_COLUMN
    from vetstats_app.analysis.patient_id_cross_table_summary import normalize_patient_id

    patient_id_col = resolve_column(patient, PATIENT_ID_COLUMN)
    species_col = resolve_column(patient, "species")
    breed_col = resolve_column(patient, "breed")
    if patient_id_col is None:
        return {}

    lookup: dict[str, tuple[object, object]] = {}
    for _, row in patient.iterrows():
        patient_id = normalize_patient_id(row[patient_id_col])
        if patient_id is None:
            continue
        species_value = row[species_col] if species_col is not None else None
        breed_value = row[breed_col] if breed_col is not None else None
        lookup[patient_id] = (species_value, breed_value)
    return lookup


def summarize_duration_values(values: tuple[float, ...]) -> DurationSummaryStats:
    if not values:
        return DurationSummaryStats(0, None, None, None, None)

    sorted_values = sorted(values)
    count = len(sorted_values)
    mean = sum(sorted_values) / count
    median = _percentile(sorted_values, 50)
    return DurationSummaryStats(
        count=count,
        mean=mean,
        median=median,
        percentile_25=_percentile(sorted_values, 25),
        percentile_75=_percentile(sorted_values, 75),
    )


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("empty values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * percentile / 100.0
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    if lower_index == upper_index:
        return sorted_values[int(rank)]
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return lower_value + (upper_value - lower_value) * (rank - lower_index)


def format_optional_number(value: float | None, *, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"
