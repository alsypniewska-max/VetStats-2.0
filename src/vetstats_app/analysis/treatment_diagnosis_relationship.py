from __future__ import annotations

from collections.abc import Iterable

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.clinical import ALLOWED_TOPICAL_SYSTEMIC, TOPICAL_SYSTEMIC_COLUMN
from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_LABELS,
    TYPE_OF_ULCER_COLUMN,
    UNKNOWN_VALUE,
    normalize_ulcer_code,
)
from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.analysis.treatment_groups import TOPICAL_SYSTEMIC_MAPPING

TREATMENT_LABELS: dict[str, str] = dict(TOPICAL_SYSTEMIC_MAPPING)
VALID_TREATMENT_CODES = frozenset(TREATMENT_LABELS)
NOT_APPLICABLE_VALUE = "x"
NON_ULCER_TYPE_CODE = "x"

SECTION_TITLE = "Powiązanie leczenia z typem wrzodu"

SUMMARY_RELATIONSHIP_TABLE_COLUMNS = (
    "Kod",
    "Rodzaj leczenia",
    "Liczba wierszy",
    "Najczęstsze typy wrzodu",
)

DETAIL_PAIR_TABLE_COLUMNS = (
    "Rodzaj leczenia",
    "Typ wrzodu",
    "Liczba wierszy",
    "Udział w typie wrzodu (%)",
)

RELATIONSHIP_COLUMNS = ("clinical_index", "treatment_code", "diagnosis_code")


@dataclass(frozen=True)
class TopUlcerCategoryRow:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class TreatmentUlcerPairRow:
    treatment_code: str
    treatment_label: str
    ulcer_code: str
    ulcer_label: str
    count: int
    ulcer_type_share_pct: float


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
    multiple_treatment_rows: int = 0
    included_ulcer_counts: tuple[TopUlcerCategoryRow, ...] = ()
    treatment_ulcer_pairs: tuple[TreatmentUlcerPairRow, ...] = ()
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def treatment_display_label(code: str) -> str:
    return TREATMENT_LABELS.get(code, code)


def format_treatment_code_legend(codes: Iterable[str]) -> str:
    seen: list[str] = []
    for code in codes:
        normalized = str(code).strip().lower()
        if normalized and normalized not in seen:
            seen.append(normalized)
    if not seen:
        return ""
    lines = [f"{code} — {treatment_display_label(code)}" for code in seen]
    return "Objaśnienie kodów leczenia:\n" + "\n".join(lines)


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


def _ulcer_relationship_frame(relationship_frame: pd.DataFrame) -> pd.DataFrame:
    if relationship_frame.empty:
        return relationship_frame
    return relationship_frame[
        relationship_frame["diagnosis_code"] != NON_ULCER_TYPE_CODE
    ].copy()


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


def _build_treatment_categories(
    relationship_frame: pd.DataFrame,
) -> tuple[TreatmentCategorySummary, ...]:
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
    return tuple(categories)


def _compute_relationship_aggregates(
    relationship_frame: pd.DataFrame,
) -> tuple[int, tuple[TopUlcerCategoryRow, ...], tuple[TreatmentUlcerPairRow, ...]]:
    if relationship_frame.empty:
        return 0, (), ()

    multiple_treatment_rows = int(
        relationship_frame.groupby("clinical_index")["treatment_code"]
        .nunique()
        .gt(1)
        .sum()
    )

    clinical_ulcer_codes = relationship_frame.groupby("clinical_index", as_index=False)[
        "diagnosis_code"
    ].first()["diagnosis_code"]
    included_ulcer_counts = tuple(
        TopUlcerCategoryRow(
            code=str(code),
            label=DIAGNOSIS_LABELS[str(code)],
            count=int(count),
        )
        for code, count in clinical_ulcer_codes.value_counts().items()
    )
    included_ulcer_counts = tuple(
        sorted(included_ulcer_counts, key=lambda row: (-row.count, row.label))
    )

    ulcer_type_totals = (
        relationship_frame.groupby("diagnosis_code")["clinical_index"]
        .nunique()
        .to_dict()
    )

    pair_rows: list[TreatmentUlcerPairRow] = []
    pair_counts = (
        relationship_frame.groupby(["treatment_code", "diagnosis_code"])["clinical_index"]
        .nunique()
        .reset_index(name="count")
    )
    for _, row in pair_counts.iterrows():
        treatment_code = str(row["treatment_code"])
        ulcer_code = str(row["diagnosis_code"])
        count = int(row["count"])
        ulcer_total = int(ulcer_type_totals.get(ulcer_code, 0))
        share_pct = (count / ulcer_total * 100.0) if ulcer_total else 0.0
        pair_rows.append(
            TreatmentUlcerPairRow(
                treatment_code=treatment_code,
                treatment_label=treatment_display_label(treatment_code),
                ulcer_code=ulcer_code,
                ulcer_label=DIAGNOSIS_LABELS[ulcer_code],
                count=count,
                ulcer_type_share_pct=share_pct,
            )
        )
    pair_rows.sort(
        key=lambda pair: (-pair.count, pair.treatment_label, pair.ulcer_label)
    )

    return multiple_treatment_rows, included_ulcer_counts, tuple(pair_rows)


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
            "Tabela pokazuje wszystkie kategorie leczenia (topical_systemic) "
            "z co najmniej jednym dopasowanym wierszem clinical."
        )

    hidden_count = total_mapped - observed_count
    return (
        "Tabela pokazuje wyłącznie kategorie leczenia (topical_systemic) "
        f"z co najmniej jednym dopasowanym wierszem clinical ({observed_count} z "
        f"{total_mapped}). Pozostałe {hidden_count} kodów z pełnego mapowania "
        "leczenia nie wystąpiły w danych z jednocześnie prawidłowym type_of_ulcer."
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
            multiple_treatment_rows=0,
            included_ulcer_counts=(),
            treatment_ulcer_pairs=(),
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

    included_cases = len(included_clinical_indices)
    ulcer_relationship_frame = _ulcer_relationship_frame(relationship_frame)
    categories = _build_treatment_categories(ulcer_relationship_frame)
    multiple_treatment_rows, included_ulcer_counts, treatment_ulcer_pairs = (
        _compute_relationship_aggregates(ulcer_relationship_frame)
    )

    return TreatmentDiagnosisRelationshipResult(
        total_cases=len(clinical),
        included_cases=included_cases,
        excluded_cases=len(clinical) - included_cases,
        source_label=source_label,
        categories=categories,
        multiple_treatment_rows=multiple_treatment_rows,
        included_ulcer_counts=included_ulcer_counts,
        treatment_ulcer_pairs=treatment_ulcer_pairs,
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
            or "Nie udało się obliczyć powiązania leczenia z typem wrzodu."
        )

    if result.included_cases == 0:
        return (
            "Brak wierszy clinical z jednocześnie prawidłowym topical_systemic "
            "i type_of_ulcer."
        )

    observed = observed_treatment_categories(result)
    if not observed:
        return (
            "Brak kategorii leczenia z dopasowanymi wierszami clinical "
            "i type_of_ulcer."
        )

    largest = max(observed, key=lambda category: category.clinical_rows)
    parts = [
        (
            f"Największa grupa leczenia: {largest.label} "
            f"({largest.clinical_rows} wierszy clinical)."
        )
    ]

    for category in observed:
        if category.top_ulcer_categories:
            parts.append(
                f"{category.label}: najczęściej type_of_ulcer = "
                f"{format_top_ulcer_categories(category.top_ulcer_categories)}."
            )

    if result.treatment_ulcer_pairs:
        strongest_pair = result.treatment_ulcer_pairs[0]
        parts.append(
            f"Najsilniejsze powiązanie: {strongest_pair.treatment_label} — "
            f"{strongest_pair.ulcer_label} ({strongest_pair.count} wierszy, "
            f"{strongest_pair.ulcer_type_share_pct:.1f}% danego typu wrzodu)."
        )

    return " ".join(parts)


def build_descriptive_stats_block(
    result: TreatmentDiagnosisRelationshipResult,
) -> ReportTableBlock:
    total_cases = result.total_cases
    included_cases = result.included_cases
    excluded_cases = result.excluded_cases
    included_pct = (included_cases / total_cases * 100.0) if total_cases else 0.0

    observed = observed_treatment_categories(result)
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
            ("Kategorie leczenia z danymi (n)", str(categories_with_data)),
            ("Największa kategoria leczenia", largest_label),
            ("Liczba — największa kategoria", largest_count),
            (
                "Typy wrzodu obecne w danych (n)",
                str(ulcer_categories_present),
            ),
            ("Najczęstszy typ wrzodu (ogółem)", most_common_ulcer_label),
            (
                "Wiersze z wieloma kategoriami leczenia (n)",
                str(result.multiple_treatment_rows),
            ),
        ),
    )
