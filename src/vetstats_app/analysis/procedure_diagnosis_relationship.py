from __future__ import annotations

from collections.abc import Iterable

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.clinical import (
    ALLOWED_SURGERY_TYPES,
    TYPE_OF_SURGERY_CODE_ORDER,
    TYPE_OF_SURGERY_COLUMN,
    TYPE_OF_SURGERY_DISPLAY_LABELS,
    TYPE_OF_SURGERY_SHORT_LABELS,
)
from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_LABELS,
    TYPE_OF_ULCER_COLUMN,
    UNKNOWN_VALUE,
    normalize_ulcer_code,
)

PROCEDURE_CODE_MAPPING: list[tuple[str, str]] = [
    (code, TYPE_OF_SURGERY_SHORT_LABELS[code]) for code in TYPE_OF_SURGERY_CODE_ORDER
]

PROCEDURE_DISPLAY_LABELS: dict[str, str] = dict(TYPE_OF_SURGERY_DISPLAY_LABELS)

SUMMARY_RELATIONSHIP_TABLE_COLUMNS = (
    "Kod",
    "Rodzaj zabiegu",
    "Liczba wierszy",
    "Najczęstsze kategorie type_of_ulcer",
)

PROCEDURE_LABELS: dict[str, str] = dict(PROCEDURE_CODE_MAPPING)
VALID_PROCEDURE_CODES = frozenset(PROCEDURE_LABELS)
NOT_APPLICABLE_VALUE = "x"
NON_ULCER_TYPE_CODE = "x"


def procedure_display_label(code: str) -> str:
    return PROCEDURE_DISPLAY_LABELS.get(code, PROCEDURE_LABELS.get(code, code))


def format_procedure_code_legend(codes: Iterable[str]) -> str:
    seen: list[str] = []
    for code in codes:
        normalized = str(code).strip().lower()
        if normalized and normalized not in seen:
            seen.append(normalized)
    if not seen:
        return ""
    lines = [f"{code} — {procedure_display_label(code)}" for code in seen]
    return "Objaśnienie kodów zabiegu:\n" + "\n".join(lines)

SECTION_TITLE = "Analiza zależności między zabiegiem a rozpoznaniem"

RELATIONSHIP_COLUMNS = ("clinical_index", "procedure_code", "diagnosis_code")


@dataclass(frozen=True)
class TopDiagnosisRow:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class ProcedureUlcerPairRow:
    procedure_code: str
    procedure_label: str
    ulcer_code: str
    ulcer_label: str
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
    multiple_procedure_rows: int = 0
    included_ulcer_counts: tuple[TopDiagnosisRow, ...] = ()
    procedure_ulcer_pairs: tuple[ProcedureUlcerPairRow, ...] = ()
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


def _ulcer_relationship_frame(relationship_frame: pd.DataFrame) -> pd.DataFrame:
    """Relationship rows with ulcer diagnoses only (excludes non-ulcer ``x``)."""
    if relationship_frame.empty:
        return relationship_frame
    return relationship_frame[
        relationship_frame["diagnosis_code"] != NON_ULCER_TYPE_CODE
    ].copy()


def _build_procedure_categories(
    relationship_frame: pd.DataFrame,
) -> tuple[ProcedureCategorySummary, ...]:
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
    return tuple(categories)


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


def _compute_relationship_aggregates(
    relationship_frame: pd.DataFrame,
) -> tuple[int, tuple[TopDiagnosisRow, ...], tuple[ProcedureUlcerPairRow, ...]]:
    if relationship_frame.empty:
        return 0, (), ()

    multiple_procedure_rows = int(
        relationship_frame.groupby("clinical_index")["procedure_code"]
        .nunique()
        .gt(1)
        .sum()
    )

    clinical_ulcer_codes = relationship_frame.groupby("clinical_index", as_index=False)[
        "diagnosis_code"
    ].first()["diagnosis_code"]
    included_ulcer_counts = tuple(
        TopDiagnosisRow(
            code=str(code),
            label=DIAGNOSIS_LABELS[str(code)],
            count=int(count),
        )
        for code, count in clinical_ulcer_codes.value_counts().items()
    )
    included_ulcer_counts = tuple(
        sorted(included_ulcer_counts, key=lambda row: (-row.count, row.label))
    )

    pair_rows: list[ProcedureUlcerPairRow] = []
    pair_counts = (
        relationship_frame.groupby(["procedure_code", "diagnosis_code"])
        .size()
        .reset_index(name="count")
    )
    for _, row in pair_counts.iterrows():
        procedure_code = str(row["procedure_code"])
        ulcer_code = str(row["diagnosis_code"])
        pair_rows.append(
            ProcedureUlcerPairRow(
                procedure_code=procedure_code,
                procedure_label=PROCEDURE_LABELS[procedure_code],
                ulcer_code=ulcer_code,
                ulcer_label=DIAGNOSIS_LABELS[ulcer_code],
                count=int(row["count"]),
            )
        )
    pair_rows.sort(
        key=lambda pair: (-pair.count, pair.procedure_label, pair.ulcer_label)
    )

    return multiple_procedure_rows, included_ulcer_counts, tuple(pair_rows)


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
            multiple_procedure_rows=0,
            included_ulcer_counts=(),
            procedure_ulcer_pairs=(),
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

    included_cases = len(included_clinical_indices)
    ulcer_relationship_frame = _ulcer_relationship_frame(relationship_frame)
    categories = _build_procedure_categories(ulcer_relationship_frame)
    multiple_procedure_rows, included_ulcer_counts, procedure_ulcer_pairs = (
        _compute_relationship_aggregates(ulcer_relationship_frame)
    )
    return ProcedureDiagnosisRelationshipResult(
        total_cases=len(clinical),
        included_cases=included_cases,
        excluded_cases=len(clinical) - included_cases,
        source_label=source_label,
        categories=categories,
        multiple_procedure_rows=multiple_procedure_rows,
        included_ulcer_counts=included_ulcer_counts,
        procedure_ulcer_pairs=procedure_ulcer_pairs,
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


def build_descriptive_stats_block(
    result: ProcedureDiagnosisRelationshipResult,
) -> ReportTableBlock:
    total_cases = result.total_cases
    included_cases = result.included_cases
    excluded_cases = result.excluded_cases
    included_pct = (included_cases / total_cases * 100.0) if total_cases else 0.0

    observed = observed_procedure_categories(result)
    categories_with_data = len(observed)

    if observed:
        largest = max(observed, key=lambda category: category.clinical_rows)
        largest_label = largest.label
        largest_count = str(largest.clinical_rows)
    else:
        largest_label = "—"
        largest_count = "0"

    ulcer_categories_present = len(
        [row for row in result.included_ulcer_counts if row.count > 0]
    )

    if result.included_ulcer_counts:
        most_common = result.included_ulcer_counts[0]
        most_common_ulcer_label = most_common.label
    else:
        most_common_ulcer_label = "—"

    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba wierszy clinical (N)", str(total_cases)),
            ("Uwzględnione wiersze (n)", str(included_cases)),
            ("Wykluczone wiersze (n)", str(excluded_cases)),
            ("Uwzględnione (%)", f"{included_pct:.1f}"),
            ("Kategorie zabiegu z danymi (n)", str(categories_with_data)),
            ("Największa kategoria zabiegu", largest_label),
            ("Liczba — największa kategoria", largest_count),
            (
                "Kategorie rozpoznania obecne w danych (n)",
                str(ulcer_categories_present),
            ),
            ("Najczęstsze rozpoznanie (ogółem)", most_common_ulcer_label),
            (
                "Wiersze z wieloma zabiegami (n)",
                str(result.multiple_procedure_rows),
            ),
        ),
    )
