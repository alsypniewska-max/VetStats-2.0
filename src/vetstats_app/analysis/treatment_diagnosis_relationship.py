from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.clinical import ALLOWED_TOPICAL_SYSTEMIC, TOPICAL_SYSTEMIC_COLUMN
from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_LABELS,
    TYPE_OF_ULCER_COLUMN,
    UNKNOWN_VALUE,
    normalize_ulcer_code,
)
from vetstats_app.analysis.treatment_groups import TOPICAL_SYSTEMIC_MAPPING

TREATMENT_LABELS: dict[str, str] = dict(TOPICAL_SYSTEMIC_MAPPING)
VALID_TREATMENT_CODES = frozenset(TREATMENT_LABELS)
NOT_APPLICABLE_VALUE = "x"

RELATIONSHIP_COLUMNS = ("clinical_index", "treatment_code", "diagnosis_code")


@dataclass(frozen=True)
class TopUlcerCategoryRow:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class TreatmentCategorySummary:
    code: str
    label: str
    clinical_rows: int
    top_ulcer_categories: tuple[TopUlcerCategoryRow, ...]


@dataclass(frozen=True)
class TreatmentDiagnosisRelationshipResult:
    total_cases: int
    included_cases: int
    excluded_cases: int
    source_label: str
    categories: tuple[TreatmentCategorySummary, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _resolve_column(clinical: pd.DataFrame, *candidates: str) -> str | None:
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in clinical.columns
    }
    for candidate in candidates:
        if candidate in clinical.columns:
            return candidate
        actual = lower_to_actual.get(candidate.lower())
        if actual is not None:
            return actual
    return None


def _split_cell_values(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    parts = [part.strip().lower() for part in str(value).split(";")]
    return [part for part in parts if part]


def normalize_treatment_codes(value: object) -> tuple[str, ...]:
    codes: list[str] = []
    for part in _split_cell_values(value):
        if not part or part in {UNKNOWN_VALUE, NOT_APPLICABLE_VALUE}:
            continue
        if part in VALID_TREATMENT_CODES and part in ALLOWED_TOPICAL_SYSTEMIC:
            if part not in codes:
                codes.append(part)
    return tuple(codes)


def _empty_relationship_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(RELATIONSHIP_COLUMNS))


def _top_ulcer_categories_for_treatment(
    treatment_rows: pd.DataFrame,
) -> tuple[TopUlcerCategoryRow, ...]:
    if treatment_rows.empty:
        return ()

    ulcer_counts = treatment_rows["diagnosis_code"].value_counts()
    if ulcer_counts.empty:
        return ()

    max_count = int(ulcer_counts.iloc[0])
    top_rows: list[TopUlcerCategoryRow] = []
    for code, count in ulcer_counts.items():
        if int(count) < max_count:
            break
        top_rows.append(
            TopUlcerCategoryRow(
                code=str(code),
                label=DIAGNOSIS_LABELS[str(code)],
                count=int(count),
            )
        )

    top_rows.sort(key=lambda row: (-row.count, row.label))
    return tuple(top_rows)


def format_top_ulcer_categories(
    top_categories: tuple[TopUlcerCategoryRow, ...],
) -> str:
    if not top_categories:
        return "—"
    return ", ".join(f"{row.label} ({row.count})" for row in top_categories)


def observed_treatment_categories(
    result: TreatmentDiagnosisRelationshipResult,
) -> tuple[TreatmentCategorySummary, ...]:
    return tuple(
        category for category in result.categories if category.clinical_rows > 0
    )


def build_table_details(result: TreatmentDiagnosisRelationshipResult) -> str:
    if not result.is_success or result.included_cases == 0:
        return ""

    observed_count = len(observed_treatment_categories(result))
    total_mapped = len(TOPICAL_SYSTEMIC_MAPPING)
    if observed_count == total_mapped:
        return (
            "Tabela pokazuje wszystkie kategorie topical_systemic z co najmniej "
            "jednym dopasowanym wierszem clinical."
        )

    hidden_count = total_mapped - observed_count
    return (
        "Tabela pokazuje wyłącznie kategorie topical_systemic z co najmniej jednym "
        f"dopasowanym wierszem clinical ({observed_count} z {total_mapped}). "
        f"Pozostałe {hidden_count} kodów z pełnego mapowania leczenia nie wystąpiły "
        "w danych z jednocześnie prawidłowym type_of_ulcer."
    )


def compute_treatment_diagnosis_relationship(
    clinical: pd.DataFrame,
    *,
    source_label: str = "clinical",
) -> TreatmentDiagnosisRelationshipResult:
    treatment_column = _resolve_column(clinical, TOPICAL_SYSTEMIC_COLUMN)
    diagnosis_column = _resolve_column(clinical, TYPE_OF_ULCER_COLUMN)

    if treatment_column is None or diagnosis_column is None:
        missing = []
        if treatment_column is None:
            missing.append("topical_systemic")
        if diagnosis_column is None:
            missing.append("type_of_ulcer")
        return TreatmentDiagnosisRelationshipResult(
            total_cases=len(clinical),
            included_cases=0,
            excluded_cases=len(clinical),
            source_label=source_label,
            categories=(),
            error_message=f"Brak kolumn w tabeli clinical: {', '.join(missing)}.",
        )

    relationship_rows: list[dict[str, object]] = []
    included_clinical_indices: set[object] = set()

    for clinical_index, row in clinical.iterrows():
        treatment_codes = normalize_treatment_codes(row[treatment_column])
        diagnosis_code = normalize_ulcer_code(row[diagnosis_column])

        if not treatment_codes or diagnosis_code is None:
            continue

        included_clinical_indices.add(clinical_index)
        for treatment_code in treatment_codes:
            relationship_rows.append(
                {
                    "clinical_index": clinical_index,
                    "treatment_code": treatment_code,
                    "diagnosis_code": diagnosis_code,
                }
            )

    relationship_frame = (
        pd.DataFrame(relationship_rows, columns=list(RELATIONSHIP_COLUMNS))
        if relationship_rows
        else _empty_relationship_frame()
    )

    categories: list[TreatmentCategorySummary] = []
    for code, label in TOPICAL_SYSTEMIC_MAPPING:
        treatment_rows = relationship_frame[
            relationship_frame["treatment_code"] == code
        ]
        clinical_rows = int(treatment_rows["clinical_index"].nunique())
        categories.append(
            TreatmentCategorySummary(
                code=code,
                label=label,
                clinical_rows=clinical_rows,
                top_ulcer_categories=_top_ulcer_categories_for_treatment(treatment_rows),
            )
        )

    included_cases = len(included_clinical_indices)
    return TreatmentDiagnosisRelationshipResult(
        total_cases=len(clinical),
        included_cases=included_cases,
        excluded_cases=len(clinical) - included_cases,
        source_label=source_label,
        categories=tuple(categories),
    )


def build_summary_details(result: TreatmentDiagnosisRelationshipResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych clinical."

    return (
        f"Źródło danych: {result.source_label}. "
        "Analiza clinical-only łączy topical_systemic z type_of_ulcer. "
        f"Uwzględniono {result.included_cases} z {result.total_cases} wierszy; "
        f"wykluczono {result.excluded_cases} wierszy bez prawidłowego kodu "
        "topical_systemic lub type_of_ulcer."
    )


def build_interpretation_summary(
    result: TreatmentDiagnosisRelationshipResult,
) -> str:
    if not result.is_success:
        return (
            result.error_message
            or "Nie udało się obliczyć powiązania topical_systemic z type_of_ulcer."
        )

    if result.included_cases == 0:
        return (
            "Brak wierszy clinical z jednocześnie prawidłowym topical_systemic "
            "i type_of_ulcer."
        )

    observed = observed_treatment_categories(result)
    if not observed:
        return (
            "Brak kategorii topical_systemic z dopasowanymi wierszami clinical "
            "i type_of_ulcer."
        )

    largest = max(observed, key=lambda category: category.clinical_rows)
    parts = [
        (
            f"Największa grupa topical_systemic: {largest.label} "
            f"({largest.clinical_rows} wierszy clinical)."
        )
    ]

    for category in observed:
        if category.top_ulcer_categories:
            parts.append(
                f"{category.label}: najczęściej type_of_ulcer = "
                f"{format_top_ulcer_categories(category.top_ulcer_categories)}."
            )

    return " ".join(parts)
