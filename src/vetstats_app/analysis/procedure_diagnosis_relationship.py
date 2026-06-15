from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.clinical import ALLOWED_SURGERY_TYPES, TYPE_OF_SURGERY_COLUMN
from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_LABELS,
    TYPE_OF_ULCER_COLUMN,
    UNKNOWN_VALUE,
    normalize_ulcer_code,
)

PROCEDURE_CODE_MAPPING: list[tuple[str, str]] = [
    ("3deb", "3DEB"),
    ("psu", "PSU"),
    ("ps", "PS"),
    ("pk", "PK"),
    ("psuk", "PSUK"),
    ("resection", "resection"),
]

PROCEDURE_LABELS: dict[str, str] = dict(PROCEDURE_CODE_MAPPING)
VALID_PROCEDURE_CODES = frozenset(PROCEDURE_LABELS)
NOT_APPLICABLE_VALUE = "x"

RELATIONSHIP_COLUMNS = ("clinical_index", "procedure_code", "diagnosis_code")


@dataclass(frozen=True)
class TopDiagnosisRow:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class ProcedureCategorySummary:
    code: str
    label: str
    clinical_rows: int
    top_diagnoses: tuple[TopDiagnosisRow, ...]


@dataclass(frozen=True)
class ProcedureDiagnosisRelationshipResult:
    total_cases: int
    included_cases: int
    excluded_cases: int
    source_label: str
    categories: tuple[ProcedureCategorySummary, ...]
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


def normalize_procedure_codes(value: object) -> tuple[str, ...]:
    codes: list[str] = []
    for part in _split_cell_values(value):
        if not part or part in {UNKNOWN_VALUE, NOT_APPLICABLE_VALUE}:
            continue
        if part in VALID_PROCEDURE_CODES and part in ALLOWED_SURGERY_TYPES:
            if part not in codes:
                codes.append(part)
    return tuple(codes)


def _empty_relationship_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(RELATIONSHIP_COLUMNS))


def _top_diagnoses_for_procedure(
    procedure_rows: pd.DataFrame,
) -> tuple[TopDiagnosisRow, ...]:
    if procedure_rows.empty:
        return ()

    diagnosis_counts = procedure_rows["diagnosis_code"].value_counts()
    if diagnosis_counts.empty:
        return ()

    max_count = int(diagnosis_counts.iloc[0])
    top_rows: list[TopDiagnosisRow] = []
    for code, count in diagnosis_counts.items():
        if int(count) < max_count:
            break
        top_rows.append(
            TopDiagnosisRow(
                code=str(code),
                label=DIAGNOSIS_LABELS[str(code)],
                count=int(count),
            )
        )

    top_rows.sort(key=lambda row: (-row.count, row.label))
    return tuple(top_rows)


def format_top_diagnoses(top_diagnoses: tuple[TopDiagnosisRow, ...]) -> str:
    if not top_diagnoses:
        return "—"
    return ", ".join(f"{row.label} ({row.count})" for row in top_diagnoses)


def observed_procedure_categories(
    result: ProcedureDiagnosisRelationshipResult,
) -> tuple[ProcedureCategorySummary, ...]:
    return tuple(
        category for category in result.categories if category.clinical_rows > 0
    )


def build_table_details(result: ProcedureDiagnosisRelationshipResult) -> str:
    if not result.is_success or result.included_cases == 0:
        return ""

    observed_count = len(observed_procedure_categories(result))
    total_mapped = len(PROCEDURE_CODE_MAPPING)
    if observed_count == total_mapped:
        return (
            "Tabela pokazuje wszystkie kategorie type_of_surgery z co najmniej "
            "jednym dopasowanym wierszem clinical."
        )

    hidden_count = total_mapped - observed_count
    return (
        "Tabela pokazuje wyłącznie kategorie type_of_surgery z co najmniej jednym "
        f"dopasowanym wierszem clinical ({observed_count} z {total_mapped}). "
        f"Pozostałe {hidden_count} kodów z pełnego mapowania procedur nie wystąpiły "
        "w danych z jednocześnie prawidłowym type_of_ulcer."
    )


def compute_procedure_diagnosis_relationship(
    clinical: pd.DataFrame,
    *,
    source_label: str = "clinical",
) -> ProcedureDiagnosisRelationshipResult:
    procedure_column = _resolve_column(clinical, TYPE_OF_SURGERY_COLUMN)
    diagnosis_column = _resolve_column(clinical, TYPE_OF_ULCER_COLUMN)

    if procedure_column is None or diagnosis_column is None:
        missing = []
        if procedure_column is None:
            missing.append("type_of_surgery")
        if diagnosis_column is None:
            missing.append("type_of_ulcer")
        return ProcedureDiagnosisRelationshipResult(
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
        procedure_codes = normalize_procedure_codes(row[procedure_column])
        diagnosis_code = normalize_ulcer_code(row[diagnosis_column])

        if not procedure_codes or diagnosis_code is None:
            continue

        included_clinical_indices.add(clinical_index)
        for procedure_code in procedure_codes:
            relationship_rows.append(
                {
                    "clinical_index": clinical_index,
                    "procedure_code": procedure_code,
                    "diagnosis_code": diagnosis_code,
                }
            )

    relationship_frame = (
        pd.DataFrame(relationship_rows, columns=list(RELATIONSHIP_COLUMNS))
        if relationship_rows
        else _empty_relationship_frame()
    )

    categories: list[ProcedureCategorySummary] = []
    for code, label in PROCEDURE_CODE_MAPPING:
        procedure_rows = relationship_frame[
            relationship_frame["procedure_code"] == code
        ]
        clinical_rows = int(procedure_rows["clinical_index"].nunique())
        categories.append(
            ProcedureCategorySummary(
                code=code,
                label=label,
                clinical_rows=clinical_rows,
                top_diagnoses=_top_diagnoses_for_procedure(procedure_rows),
            )
        )

    included_cases = len(included_clinical_indices)
    return ProcedureDiagnosisRelationshipResult(
        total_cases=len(clinical),
        included_cases=included_cases,
        excluded_cases=len(clinical) - included_cases,
        source_label=source_label,
        categories=tuple(categories),
    )


def build_summary_details(result: ProcedureDiagnosisRelationshipResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych clinical."

    return (
        f"Źródło danych: {result.source_label}. "
        "Analiza clinical-only łączy type_of_surgery z type_of_ulcer. "
        f"Uwzględniono {result.included_cases} z {result.total_cases} wierszy; "
        f"wykluczono {result.excluded_cases} wierszy bez prawidłowego kodu "
        "type_of_surgery lub type_of_ulcer."
    )


def build_interpretation_summary(
    result: ProcedureDiagnosisRelationshipResult,
) -> str:
    if not result.is_success:
        return (
            result.error_message
            or "Nie udało się obliczyć powiązania type_of_surgery z type_of_ulcer."
        )

    if result.included_cases == 0:
        return (
            "Brak wierszy clinical z jednocześnie prawidłowym type_of_surgery "
            "i type_of_ulcer."
        )

    observed = observed_procedure_categories(result)
    if not observed:
        return (
            "Brak kategorii type_of_surgery z dopasowanymi wierszami clinical "
            "i type_of_ulcer."
        )

    largest = max(observed, key=lambda category: category.clinical_rows)
    parts = [
        (
            f"Największa grupa type_of_surgery: {largest.label} "
            f"({largest.clinical_rows} wierszy clinical)."
        )
    ]

    for category in observed:
        if category.top_diagnoses:
            parts.append(
                f"{category.label}: najczęściej type_of_ulcer = "
                f"{format_top_diagnoses(category.top_diagnoses)}."
            )

    return " ".join(parts)
