from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from data_sterilizer.schemas.patient import (
    DATE_OF_BIRTH_COLUMN,
    EMPTY_VALUE_REPLACEMENT,
    PATIENT_ID_COLUMN,
    is_valid_date_of_birth,
)

SPECIES_COLUMN = "species"
BREED_COLUMN = "breed"

UNKNOWN_VALUE = EMPTY_VALUE_REPLACEMENT
DOG_SPECIES = frozenset({"dog", "pies"})
CAT_SPECIES = frozenset({"cat", "kot"})


@dataclass(frozen=True)
class CategoryCountRow:
    label: str
    count: int


@dataclass(frozen=True)
class PopulationCharacteristicsResult:
    total_patients: int
    total_records: int
    species_count: int
    source_label: str
    species_counts: tuple[CategoryCountRow, ...]
    dog_breed_counts: tuple[CategoryCountRow, ...]
    cat_breed_counts: tuple[CategoryCountRow, ...]
    age_years: tuple[float, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _resolve_column(patient: pd.DataFrame, *candidates: str) -> str | None:
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in patient.columns
    }
    for candidate in candidates:
        if candidate in patient.columns:
            return candidate
        actual = lower_to_actual.get(candidate.lower())
        if actual is not None:
            return actual
    return None


def _normalize_text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower()
    if not text or text == UNKNOWN_VALUE:
        return None
    return text


def _parse_age_years(value: object, *, reference_date: datetime) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not is_valid_date_of_birth(text):
        return None
    day_text, month_text, year_text = text.split(".")
    birth_date = datetime(int(year_text), int(month_text), int(day_text))
    age_days = (reference_date - birth_date).days
    if age_days < 0:
        return None
    return age_days / 365.25


def _count_by_column(values: pd.Series) -> tuple[CategoryCountRow, ...]:
    normalized = values.map(_normalize_text).dropna()
    if normalized.empty:
        return ()
    counts = normalized.value_counts()
    return tuple(
        CategoryCountRow(label=str(label), count=int(count))
        for label, count in counts.items()
    )


def compute_population_characteristics(
    patient: pd.DataFrame,
    *,
    source_label: str = "patient",
    reference_date: datetime | None = None,
) -> PopulationCharacteristicsResult:
    species_column = _resolve_column(patient, SPECIES_COLUMN)
    breed_column = _resolve_column(patient, BREED_COLUMN)
    birth_column = _resolve_column(patient, DATE_OF_BIRTH_COLUMN)
    patient_id_column = _resolve_column(patient, PATIENT_ID_COLUMN)

    if species_column is None or breed_column is None:
        missing = []
        if species_column is None:
            missing.append("species")
        if breed_column is None:
            missing.append("breed")
        return PopulationCharacteristicsResult(
            total_patients=0,
            total_records=len(patient),
            species_count=0,
            source_label=source_label,
            species_counts=(),
            dog_breed_counts=(),
            cat_breed_counts=(),
            age_years=(),
            error_message=f"Brak kolumn w tabeli patient: {', '.join(missing)}.",
        )

    reference = reference_date or datetime.now()
    species_series = patient[species_column]
    breed_series = patient[breed_column]
    species_counts = _count_by_column(species_series)

    dog_mask = species_series.map(_normalize_text).isin(DOG_SPECIES)
    cat_mask = species_series.map(_normalize_text).isin(CAT_SPECIES)
    dog_breed_counts = _count_by_column(breed_series[dog_mask])
    cat_breed_counts = _count_by_column(breed_series[cat_mask])

    age_years: list[float] = []
    if birth_column is not None:
        for value in patient[birth_column]:
            age = _parse_age_years(value, reference_date=reference)
            if age is not None:
                age_years.append(age)

    unique_patients = 0
    if patient_id_column is not None:
        unique_patients = int(patient[patient_id_column].map(_normalize_text).dropna().nunique())
    else:
        unique_patients = len(patient)

    return PopulationCharacteristicsResult(
        total_patients=unique_patients,
        total_records=len(patient),
        species_count=len(species_counts),
        source_label=source_label,
        species_counts=species_counts,
        dog_breed_counts=dog_breed_counts,
        cat_breed_counts=cat_breed_counts,
        age_years=tuple(age_years),
    )


def build_summary_details(result: PopulationCharacteristicsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych patient."

    return (
        f"Źródło danych: {result.source_label}. "
        f"Przeanalizowano {result.total_records} rekordów patient "
        f"({result.total_patients} unikalnych patient_ID, "
        f"{result.species_count} gatunków)."
    )


def build_interpretation_summary(result: PopulationCharacteristicsResult) -> str:
    if not result.is_success:
        return (
            result.error_message
            or "Nie udało się obliczyć charakterystyki populacji pacjentów."
        )

    parts: list[str] = []
    if result.species_counts:
        largest_species = max(result.species_counts, key=lambda row: row.count)
        parts.append(
            f"Dominujący gatunek: {largest_species.label} ({largest_species.count})."
        )
    if result.dog_breed_counts:
        largest_dog_breed = max(result.dog_breed_counts, key=lambda row: row.count)
        parts.append(
            f"Najczęstsza rasa u psów: {largest_dog_breed.label} "
            f"({largest_dog_breed.count})."
        )
    if result.cat_breed_counts:
        largest_cat_breed = max(result.cat_breed_counts, key=lambda row: row.count)
        parts.append(
            f"Najczęstsza rasa u kotów: {largest_cat_breed.label} "
            f"({largest_cat_breed.count})."
        )
    if result.age_years:
        average_age = sum(result.age_years) / len(result.age_years)
        parts.append(
            f"Średni wiek pacjentów z prawidłową datą urodzenia: {average_age:.1f} lat "
            f"(n={len(result.age_years)})."
        )

    if not parts:
        return "Brak danych do krótkiej interpretacji charakterystyki populacji."
    return " ".join(parts)
