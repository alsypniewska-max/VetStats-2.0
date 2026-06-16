from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from vetstats_app.analysis.report_models import ReportTableBlock

TYPE_OF_ULCER_COLUMN = "type_of_ulcer"
FARMACOLOGY_SURGERY_COLUMNS = ("farmacology_surgery", "pharmacology_surgery")
TOPICAL_SYSTEMIC_COLUMN = "topical_systemic"
HOW_ENDED_COLUMN = "how_ended"
UNKNOWN_VALUE = "xxx"

FARMACOLOGY_SURGERY_MAPPING: list[tuple[str, str]] = [
    ("f", "farmakologia"),
    ("s", "farmakologia + chirurgia"),
]

TOPICAL_SYSTEMIC_MAPPING: list[tuple[str, str]] = [
    ("t", "miejscowe"),
    ("s", "ogólne"),
    ("ts", "miejscowe + ogólne"),
]

VALID_FARMACOLOGY_CODES = frozenset(code for code, _ in FARMACOLOGY_SURGERY_MAPPING)
VALID_TOPICAL_SYSTEMIC_CODES = frozenset(code for code, _ in TOPICAL_SYSTEMIC_MAPPING)
REAL_ULCER_CODES = frozenset({"s", "e", "p", "n", "m", "sceed"})

HOW_ENDED_GOOD = "good"
HOW_ENDED_CONTINUATION = "continuation"


@dataclass(frozen=True)
class TreatmentCategoryRow:
    code: str
    label: str
    count: int
    percentage: float


@dataclass(frozen=True)
class UlcerTreatmentSuccess:
    eligible_cases: int
    excluded_continuation: int
    evaluated_cases: int
    success_count: int
    success_rate: float


@dataclass(frozen=True)
class TreatmentGroupsResult:
    total_cases: int
    source_label: str
    pharmacology_included_cases: int
    pharmacology_excluded_cases: int
    pharmacology_rows: tuple[TreatmentCategoryRow, ...]
    topical_included_cases: int
    topical_excluded_cases: int
    topical_rows: tuple[TreatmentCategoryRow, ...]
    ulcer_success: UlcerTreatmentSuccess
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


def _first_valid_code(values: list[str], allowed_codes: frozenset[str]) -> str | None:
    for value in values:
        if not value or value == UNKNOWN_VALUE:
            continue
        if value in allowed_codes:
            return value
    return None


def _normalize_real_ulcer_code(value: object) -> str | None:
    values = _split_cell_values(value)
    if not values:
        return None

    code = values[0]
    if code == UNKNOWN_VALUE or code not in REAL_ULCER_CODES:
        return None
    return code


def _normalize_how_ended(value: object) -> str | None:
    values = _split_cell_values(value)
    if not values:
        return None

    code = values[0]
    if not code or code == UNKNOWN_VALUE:
        return None
    return code


def _build_category_rows(
    codes: pd.Series,
    mapping: list[tuple[str, str]],
) -> tuple[int, int, tuple[TreatmentCategoryRow, ...]]:
    total_cases = len(codes)
    included_codes = codes.dropna()
    included_cases = len(included_codes)
    excluded_cases = total_cases - included_cases
    counts = included_codes.value_counts()

    rows: list[TreatmentCategoryRow] = []
    for code, label in mapping:
        count = int(counts.get(code, 0))
        percentage = (count / included_cases * 100.0) if included_cases else 0.0
        rows.append(
            TreatmentCategoryRow(
                code=code,
                label=label,
                count=count,
                percentage=percentage,
            )
        )

    return included_cases, excluded_cases, tuple(rows)


def compute_treatment_groups(
    clinical: pd.DataFrame,
    *,
    source_label: str = "clinical",
) -> TreatmentGroupsResult:
    pharmacology_column = _resolve_column(clinical, *FARMACOLOGY_SURGERY_COLUMNS)
    topical_column = _resolve_column(clinical, TOPICAL_SYSTEMIC_COLUMN)
    ulcer_column = _resolve_column(clinical, TYPE_OF_ULCER_COLUMN)
    how_ended_column = _resolve_column(clinical, HOW_ENDED_COLUMN)

    missing_columns = [
        name
        for name, column in (
            ("farmacology_surgery", pharmacology_column),
            ("topical_systemic", topical_column),
            ("type_of_ulcer", ulcer_column),
            ("how_ended", how_ended_column),
        )
        if column is None
    ]
    if missing_columns:
        return TreatmentGroupsResult(
            total_cases=len(clinical),
            source_label=source_label,
            pharmacology_included_cases=0,
            pharmacology_excluded_cases=len(clinical),
            pharmacology_rows=(),
            topical_included_cases=0,
            topical_excluded_cases=len(clinical),
            topical_rows=(),
            ulcer_success=UlcerTreatmentSuccess(0, 0, 0, 0, 0.0),
            error_message=(
                "Brak wymaganych kolumn w tabeli clinical: "
                + ", ".join(missing_columns)
                + "."
            ),
        )

    total_cases = len(clinical)

    pharmacology_codes = clinical[pharmacology_column].map(
        lambda value: _first_valid_code(_split_cell_values(value), VALID_FARMACOLOGY_CODES)
    )
    pharmacology_included, pharmacology_excluded, pharmacology_rows = _build_category_rows(
        pharmacology_codes,
        FARMACOLOGY_SURGERY_MAPPING,
    )

    topical_codes = clinical[topical_column].map(
        lambda value: _first_valid_code(
            _split_cell_values(value),
            VALID_TOPICAL_SYSTEMIC_CODES,
        )
    )
    topical_included, topical_excluded, topical_rows = _build_category_rows(
        topical_codes,
        TOPICAL_SYSTEMIC_MAPPING,
    )

    ulcer_mask = clinical[ulcer_column].map(_normalize_real_ulcer_code).notna()
    eligible_cases = int(ulcer_mask.sum())
    how_ended_values = clinical.loc[ulcer_mask, how_ended_column].map(_normalize_how_ended)
    continuation_mask = how_ended_values == HOW_ENDED_CONTINUATION
    excluded_continuation = int(continuation_mask.sum())
    evaluated_mask = how_ended_values.notna() & ~continuation_mask
    evaluated_cases = int(evaluated_mask.sum())
    success_count = int((how_ended_values[evaluated_mask] == HOW_ENDED_GOOD).sum())
    success_rate = (
        success_count / evaluated_cases * 100.0 if evaluated_cases else 0.0
    )

    return TreatmentGroupsResult(
        total_cases=total_cases,
        source_label=source_label,
        pharmacology_included_cases=pharmacology_included,
        pharmacology_excluded_cases=pharmacology_excluded,
        pharmacology_rows=pharmacology_rows,
        topical_included_cases=topical_included,
        topical_excluded_cases=topical_excluded,
        topical_rows=topical_rows,
        ulcer_success=UlcerTreatmentSuccess(
            eligible_cases=eligible_cases,
            excluded_continuation=excluded_continuation,
            evaluated_cases=evaluated_cases,
            success_count=success_count,
            success_rate=success_rate,
        ),
    )


def build_summary_details(result: TreatmentGroupsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych clinical."

    return (
        f"Źródło danych: {result.source_label}. "
        f"Przeanalizowano {result.total_cases} przypadków klinicznych "
        f"na podstawie tabeli clinical."
    )


def build_interpretation_summary(result: TreatmentGroupsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się obliczyć analizy leczenia."

    parts: list[str] = []

    pharmacology_observed = [
        row for row in result.pharmacology_rows if row.count > 0
    ]
    if pharmacology_observed:
        most_common_pharmacology = max(
            pharmacology_observed,
            key=lambda row: (row.count, row.label),
        )
        parts.append(
            "Najczęstszy podział farmacology_surgery: "
            f"{most_common_pharmacology.label} "
            f"({most_common_pharmacology.count}, {most_common_pharmacology.percentage:.1f}%)."
        )

    topical_observed = [row for row in result.topical_rows if row.count > 0]
    if topical_observed:
        most_common_topical = max(
            topical_observed,
            key=lambda row: (row.count, row.label),
        )
        parts.append(
            "Najczęstszy wzorzec topical_systemic: "
            f"{most_common_topical.label} "
            f"({most_common_topical.count}, {most_common_topical.percentage:.1f}%)."
        )

    ulcer_success = result.ulcer_success
    if ulcer_success.eligible_cases == 0:
        parts.append("Brak przypadków wrzodowych do oceny skuteczności leczenia.")
    elif ulcer_success.evaluated_cases == 0:
        parts.append(
            "Brak przypadków wrzodowych z możliwą oceną skuteczności "
            f"(wykluczono {ulcer_success.excluded_continuation} z continuation)."
        )
    else:
        parts.append(
            "Skuteczność leczenia wrzodów: "
            f"{ulcer_success.success_count} z {ulcer_success.evaluated_cases} "
            f"({ulcer_success.success_rate:.1f}%) zakończone jako good "
            f"(z {ulcer_success.eligible_cases} przypadków wrzodowych; "
            f"wykluczono {ulcer_success.excluded_continuation} continuation)."
        )

    return " ".join(parts)


def build_descriptive_stats_block(
    result: TreatmentGroupsResult,
) -> ReportTableBlock:
    total_n = result.total_cases
    pharmacology_included = result.pharmacology_included_cases
    pharmacology_excluded = result.pharmacology_excluded_cases
    pharmacology_included_pct = (
        (pharmacology_included / total_n * 100.0) if total_n else 0.0
    )
    pharmacology_excluded_pct = (
        (pharmacology_excluded / total_n * 100.0) if total_n else 0.0
    )

    topical_included = result.topical_included_cases
    topical_excluded = result.topical_excluded_cases
    topical_included_pct = (topical_included / total_n * 100.0) if total_n else 0.0
    topical_excluded_pct = (topical_excluded / total_n * 100.0) if total_n else 0.0

    pharmacology_nonzero = sum(1 for row in result.pharmacology_rows if row.count > 0)
    topical_nonzero = sum(1 for row in result.topical_rows if row.count > 0)

    ulcer_success = result.ulcer_success

    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba przypadków (N)", str(total_n)),
            ("Farmacology_surgery — uwzględnione (n)", str(pharmacology_included)),
            ("Farmacology_surgery — wykluczone (n)", str(pharmacology_excluded)),
            ("Farmacology_surgery — uwzględnione (%)", f"{pharmacology_included_pct:.1f}"),
            ("Farmacology_surgery — wykluczone (%)", f"{pharmacology_excluded_pct:.1f}"),
            (
                "Farmacology_surgery — kategorie z danymi",
                str(pharmacology_nonzero),
            ),
            ("Topical_systemic — uwzględnione (n)", str(topical_included)),
            ("Topical_systemic — wykluczone (n)", str(topical_excluded)),
            ("Topical_systemic — uwzględnione (%)", f"{topical_included_pct:.1f}"),
            ("Topical_systemic — wykluczone (%)", f"{topical_excluded_pct:.1f}"),
            ("Topical_systemic — kategorie z danymi", str(topical_nonzero)),
            (
                "Przypadki wrzodowe (eligible) (n)",
                str(ulcer_success.eligible_cases),
            ),
            ("Ocenione przypadki (n)", str(ulcer_success.evaluated_cases)),
            ("Zakończone jako good (n)", str(ulcer_success.success_count)),
            ("Skuteczność (%)", f"{ulcer_success.success_rate:.1f}"),
            (
                "Wykluczone continuation (n)",
                str(ulcer_success.excluded_continuation),
            ),
        ),
    )
