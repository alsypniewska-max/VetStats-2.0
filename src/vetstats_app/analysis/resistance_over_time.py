from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.micro import (
    BACTERIA_COLUMN,
    DATE_COLLECT_COLUMN,
    NEGATIVE_BACTERIA_VALUE,
    SUSCEPTIBILITY_COLUMNS,
    parse_micro_date,
)

UNKNOWN_VALUE = "xxx"
ANALYSIS_YEARS: tuple[int, ...] = (2024, 2025, 2026)

SENSITIVITY_CATEGORY_MAPPING: list[tuple[str, str]] = [
    ("+++", "wysoka wrażliwość (+++)"),
    ("+", "wrażliwość (+)"),
    ("0", "oporność (0)"),
    ("x", "nie dotyczy (x)"),
]

VALID_SENSITIVITY_CODES = frozenset(code for code, _ in SENSITIVITY_CATEGORY_MAPPING)


@dataclass(frozen=True)
class SensitivityCategoryRow:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class YearlyResistanceSummary:
    year: int
    included_observations: int
    most_common_bacteria: str | None
    most_common_bacteria_count: int
    sensitivity_counts: tuple[SensitivityCategoryRow, ...]


@dataclass(frozen=True)
class ExclusionSummary:
    total_micro_rows: int
    excluded_negative: int
    excluded_invalid_bacteria: int
    excluded_invalid_year: int
    included_total: int


@dataclass(frozen=True)
class ResistanceOverTimeResult:
    source_label: str
    exclusions: ExclusionSummary
    yearly_summaries: tuple[YearlyResistanceSummary, ...]
    has_sensitivity_data: bool
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _resolve_column(micro: pd.DataFrame, *candidates: str) -> str | None:
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in micro.columns
    }
    for candidate in candidates:
        if candidate in micro.columns:
            return candidate
        actual = lower_to_actual.get(candidate.lower())
        if actual is not None:
            return actual
    return None


def _normalize_bacteria(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower()
    if not text or text == UNKNOWN_VALUE:
        return None
    return text


def _extract_year(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = parse_micro_date(str(value).strip())
    if parsed is None:
        return None
    year = parsed.year
    if year not in ANALYSIS_YEARS:
        return None
    return year


def _normalize_sensitivity(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower()
    if not text or text == UNKNOWN_VALUE:
        return None
    if text in VALID_SENSITIVITY_CODES:
        return text
    return None


def _resolve_susceptibility_columns(micro: pd.DataFrame) -> list[str]:
    columns: list[str] = []
    for candidate in SUSCEPTIBILITY_COLUMNS:
        actual = _resolve_column(micro, candidate)
        if actual is not None:
            columns.append(actual)
    return columns


def _build_sensitivity_counts(
    micro_rows: pd.DataFrame,
    susceptibility_columns: list[str],
) -> tuple[SensitivityCategoryRow, ...]:
    if micro_rows.empty or not susceptibility_columns:
        return tuple(
            SensitivityCategoryRow(code=code, label=label, count=0)
            for code, label in SENSITIVITY_CATEGORY_MAPPING
        )

    values = micro_rows[susceptibility_columns].stack(future_stack=True)
    normalized = values.map(_normalize_sensitivity).dropna()
    counts = normalized.value_counts()

    return tuple(
        SensitivityCategoryRow(
            code=code,
            label=label,
            count=int(counts.get(code, 0)),
        )
        for code, label in SENSITIVITY_CATEGORY_MAPPING
    )


def compute_resistance_over_time(
    micro: pd.DataFrame,
    *,
    source_label: str = "micro",
) -> ResistanceOverTimeResult:
    bacteria_col = _resolve_column(micro, BACTERIA_COLUMN)
    date_collect_col = _resolve_column(micro, DATE_COLLECT_COLUMN)

    if bacteria_col is None or date_collect_col is None:
        missing = []
        if bacteria_col is None:
            missing.append("bacteria")
        if date_collect_col is None:
            missing.append("date_collect")
        return ResistanceOverTimeResult(
            source_label=source_label,
            exclusions=ExclusionSummary(0, 0, 0, 0, 0),
            yearly_summaries=(),
            has_sensitivity_data=False,
            error_message=(
                "Brak wymaganych kolumn w tabeli micro: "
                + ", ".join(missing)
                + "."
            ),
        )

    total_micro_rows = len(micro)
    normalized_bacteria = micro[bacteria_col].map(_normalize_bacteria)

    # Excluded from resistance analysis: negative microbiology results,
    # missing/invalid bacteria values, and rows outside 2024-2026 date_collect.
    negative_mask = normalized_bacteria == NEGATIVE_BACTERIA_VALUE
    invalid_bacteria_mask = normalized_bacteria.isna() & ~negative_mask
    valid_bacteria_mask = normalized_bacteria.notna() & ~negative_mask

    work = micro.loc[valid_bacteria_mask].copy()
    work["_bacteria"] = normalized_bacteria[valid_bacteria_mask]
    work["_year"] = work[date_collect_col].map(_extract_year)

    invalid_year_mask = work["_year"].isna()
    included = work.loc[~invalid_year_mask].copy()

    exclusions = ExclusionSummary(
        total_micro_rows=total_micro_rows,
        excluded_negative=int(negative_mask.sum()),
        excluded_invalid_bacteria=int(invalid_bacteria_mask.sum()),
        excluded_invalid_year=int(invalid_year_mask.sum()),
        included_total=len(included),
    )

    susceptibility_columns = _resolve_susceptibility_columns(micro)
    has_sensitivity_data = bool(susceptibility_columns)

    yearly_summaries: list[YearlyResistanceSummary] = []
    for year in ANALYSIS_YEARS:
        year_rows = included[included["_year"] == year]
        included_observations = len(year_rows)

        most_common_bacteria: str | None = None
        most_common_bacteria_count = 0
        if included_observations > 0:
            bacteria_counts = year_rows["_bacteria"].value_counts()
            most_common_bacteria = str(bacteria_counts.index[0])
            most_common_bacteria_count = int(bacteria_counts.iloc[0])

        sensitivity_counts = _build_sensitivity_counts(
            year_rows,
            susceptibility_columns,
        )

        yearly_summaries.append(
            YearlyResistanceSummary(
                year=year,
                included_observations=included_observations,
                most_common_bacteria=most_common_bacteria,
                most_common_bacteria_count=most_common_bacteria_count,
                sensitivity_counts=sensitivity_counts,
            )
        )

    return ResistanceOverTimeResult(
        source_label=source_label,
        exclusions=exclusions,
        yearly_summaries=tuple(yearly_summaries),
        has_sensitivity_data=has_sensitivity_data,
    )


def build_summary_details(result: ResistanceOverTimeResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych micro."

    exclusions = result.exclusions
    return (
        f"Źródło danych: {result.source_label}. "
        f"Uwzględniono {exclusions.included_total} z {exclusions.total_micro_rows} "
        f"wierszy micro w analizie rocznej 2024–2026."
    )


def build_inclusion_details(result: ResistanceOverTimeResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się określić kryteriów włączenia danych."

    exclusions = result.exclusions
    return (
        f"Wykluczono {exclusions.excluded_negative} wierszy z bacteria = negative, "
        f"{exclusions.excluded_invalid_bacteria} wierszy z brakującymi lub "
        f"nieprawidłowymi wartościami bacteria oraz "
        f"{exclusions.excluded_invalid_year} wierszy z brakującą datą date_collect "
        f"lub rokiem spoza 2024–2026."
    )


def build_interpretation_summary(result: ResistanceOverTimeResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się obliczyć analizy oporności w czasie."

    if result.exclusions.included_total == 0:
        return "Brak obserwacji micro spełniających kryteria analizy oporności w czasie."

    parts: list[str] = []
    observed_years = [
        summary
        for summary in result.yearly_summaries
        if summary.included_observations > 0
    ]
    if observed_years:
        busiest_year = max(
            observed_years,
            key=lambda summary: summary.included_observations,
        )
        parts.append(
            f"Najwięcej obserwacji w {busiest_year.year}: "
            f"{busiest_year.included_observations}."
        )
        for summary in observed_years:
            if summary.most_common_bacteria:
                parts.append(
                    f"{summary.year}: najczęstsza bakteria "
                    f"{summary.most_common_bacteria} "
                    f"({summary.most_common_bacteria_count})."
                )

    if result.has_sensitivity_data:
        resistance_by_year = []
        for summary in observed_years:
            resistant = next(
                (row.count for row in summary.sensitivity_counts if row.code == "0"),
                0,
            )
            resistance_by_year.append(f"{summary.year}: {resistant} oporności (0)")
        if resistance_by_year:
            parts.append(
                "Zagregowane obserwacje wrażliwości (growth + antybiotyki): "
                + "; ".join(resistance_by_year)
                + "."
            )

    return " ".join(parts)
