from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from data_sterilizer.schemas.micro import DATE_COLLECT_COLUMN, RESULT_ID_COLUMN, parse_micro_date
from vetstats_app.analysis.clinical_common import resolve_column
from vetstats_app.analysis.report_models import ReportTableBlock

POLISH_MONTH_LABELS: tuple[str, ...] = (
    "Styczeń",
    "Luty",
    "Marzec",
    "Kwiecień",
    "Maj",
    "Czerwiec",
    "Lipiec",
    "Sierpień",
    "Wrzesień",
    "Październik",
    "Listopad",
    "Grudzień",
)


@dataclass(frozen=True)
class SwabCollectionRecord:
    collect_date: date
    result_id: str


@dataclass(frozen=True)
class MonthlyCountRow:
    month: int
    month_label: str
    count: int
    percentage: float


@dataclass(frozen=True)
class YearlyMonthlyDistribution:
    year: int
    total_swabs: int
    months: tuple[MonthlyCountRow, ...]


@dataclass(frozen=True)
class MicroMonthlyDistributionResult:
    source_label: str
    total_rows: int
    excluded_invalid_date_collect: int
    excluded_missing_result_id: int
    included_swabs: int
    observed_years: tuple[int, ...]
    yearly_distributions: tuple[YearlyMonthlyDistribution, ...]
    combined_distribution: YearlyMonthlyDistribution
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _parse_collect_date(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "xxx":
        return None
    parsed = parse_micro_date(text)
    if parsed is None:
        return None
    return parsed.date()


def _normalize_result_id(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "xxx":
        return None
    return text


def observed_years_from_records(
    records: tuple[SwabCollectionRecord, ...],
) -> tuple[int, ...]:
    return tuple(sorted({record.collect_date.year for record in records}))


def build_monthly_distribution(
    records: tuple[SwabCollectionRecord, ...],
    *,
    year: int | None = None,
) -> YearlyMonthlyDistribution:
    filtered = tuple(
        record
        for record in records
        if year is None or record.collect_date.year == year
    )
    result_ids_by_month: list[set[str]] = [set() for _ in range(12)]
    for record in filtered:
        result_ids_by_month[record.collect_date.month - 1].add(record.result_id)

    total_swabs = len({record.result_id for record in filtered})
    rows: list[MonthlyCountRow] = []
    for month_index, label in enumerate(POLISH_MONTH_LABELS, start=1):
        count = len(result_ids_by_month[month_index - 1])
        percentage = (count / total_swabs * 100.0) if total_swabs else 0.0
        rows.append(
            MonthlyCountRow(
                month=month_index,
                month_label=label,
                count=count,
                percentage=percentage,
            )
        )
    return YearlyMonthlyDistribution(
        year=year or 0,
        total_swabs=total_swabs,
        months=tuple(rows),
    )


def _empty_result(
    *,
    source_label: str,
    total_rows: int,
    error_message: str,
) -> MicroMonthlyDistributionResult:
    return MicroMonthlyDistributionResult(
        source_label=source_label,
        total_rows=total_rows,
        excluded_invalid_date_collect=total_rows,
        excluded_missing_result_id=0,
        included_swabs=0,
        observed_years=(),
        yearly_distributions=(),
        combined_distribution=build_monthly_distribution(()),
        error_message=error_message,
    )


def compute_micro_monthly_distribution(
    micro: pd.DataFrame,
    *,
    source_label: str = "micro",
) -> MicroMonthlyDistributionResult:
    date_column = resolve_column(micro, DATE_COLLECT_COLUMN)
    result_id_column = resolve_column(micro, RESULT_ID_COLUMN)
    if date_column is None or result_id_column is None:
        missing = []
        if date_column is None:
            missing.append(DATE_COLLECT_COLUMN)
        if result_id_column is None:
            missing.append(RESULT_ID_COLUMN)
        return _empty_result(
            source_label=source_label,
            total_rows=len(micro),
            error_message=(
                "Brak wymaganych kolumn w tabeli micro: " + ", ".join(missing) + "."
            ),
        )

    total_rows = len(micro)
    parsed_dates = micro[date_column].map(_parse_collect_date)
    parsed_result_ids = micro[result_id_column].map(_normalize_result_id)

    invalid_date_mask = parsed_dates.isna()
    excluded_invalid_date_collect = int(invalid_date_mask.sum())

    valid_date_mask = ~invalid_date_mask
    missing_result_id_mask = valid_date_mask & parsed_result_ids.isna()
    excluded_missing_result_id = int(missing_result_id_mask.sum())

    included_mask = valid_date_mask & parsed_result_ids.notna()
    swab_records = tuple(
        SwabCollectionRecord(
            collect_date=parsed_dates.loc[row_index],
            result_id=parsed_result_ids.loc[row_index],
        )
        for row_index in micro.index[included_mask]
    )

    observed_years = observed_years_from_records(swab_records)
    yearly_distributions = tuple(
        build_monthly_distribution(swab_records, year=year)
        for year in observed_years
    )
    combined = build_monthly_distribution(swab_records)

    return MicroMonthlyDistributionResult(
        source_label=source_label,
        total_rows=total_rows,
        excluded_invalid_date_collect=excluded_invalid_date_collect,
        excluded_missing_result_id=excluded_missing_result_id,
        included_swabs=len({record.result_id for record in swab_records}),
        observed_years=observed_years,
        yearly_distributions=yearly_distributions,
        combined_distribution=combined,
    )


def build_summary_details(result: MicroMonthlyDistributionResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przeanalizować rozkładu wymazów."

    year_span = (
        ", ".join(str(year) for year in result.observed_years)
        if result.observed_years
        else "brak lat z danymi"
    )
    parts = [
        f"Źródło danych: {result.source_label}.",
        (
            f"Uwzględniono {result.included_swabs} unikalnych result_ID "
            f"(pobrań wymazów) z {result.total_rows} wierszy micro."
        ),
        (
            f"Wykluczono {result.excluded_invalid_date_collect} wierszy "
            f"z nieprawidłową date_collect"
        ),
    ]
    if result.excluded_missing_result_id:
        parts.append(
            f"oraz {result.excluded_missing_result_id} wierszy bez prawidłowego result_ID"
        )
    parts.append(f"Lata w danych: {year_span}.")
    return " ".join(parts)


def build_interpretation_summary(result: MicroMonthlyDistributionResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przygotować interpretacji."

    if result.included_swabs == 0:
        return "Brak wymazów z prawidłową datą pobrania do analizy miesięcznej."

    combined = result.combined_distribution
    busiest = max(combined.months, key=lambda row: (row.count, -row.month))
    quietest = min(
        [row for row in combined.months if row.count > 0] or combined.months,
        key=lambda row: (row.count, row.month),
    )
    return (
        f"W analizie łącznej ({result.included_swabs} unikalnych result_ID) najwięcej "
        f"pobrań przypada na {busiest.month_label.lower()} ({busiest.count}), "
        f"najmniej na {quietest.month_label.lower()} ({quietest.count}). "
        f"Wygenerowano {len(result.yearly_distributions)} widoków rocznych oraz "
        f"1 widok łączny."
    )


def build_descriptive_stats_block(
    result: MicroMonthlyDistributionResult,
) -> ReportTableBlock:
    rows: list[tuple[str, str]] = [
        ("Łączna liczba wierszy micro (N)", str(result.total_rows)),
        (
            "Wykluczone — nieprawidłowa date_collect (n)",
            str(result.excluded_invalid_date_collect),
        ),
        (
            "Wykluczone — brak prawidłowego result_ID (n)",
            str(result.excluded_missing_result_id),
        ),
        (
            "Uwzględnione wymazy — unikalne result_ID (n)",
            str(result.included_swabs),
        ),
        ("Lata z danymi (n)", str(len(result.observed_years))),
        (
            "Lata",
            ", ".join(str(year) for year in result.observed_years) or "—",
        ),
        ("Widoki roczne (tabele/wykresy)", str(len(result.yearly_distributions))),
        ("Widok łączny (tabela/wykres)", "1"),
    ]
    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=tuple(rows),
    )


def monthly_distribution_table_block(
    distribution: YearlyMonthlyDistribution,
    *,
    combined: bool = False,
) -> ReportTableBlock:
    title = (
        "Rozkład wymazów według miesiąca — wszystkie lata"
        if combined
        else f"Rozkład wymazów według miesiąca — {distribution.year}"
    )
    return ReportTableBlock(
        title=title,
        columns=("Miesiąc", "Liczba wymazów", "Udział (%)"),
        rows=tuple(
            (row.month_label, str(row.count), f"{row.percentage:.1f}")
            for row in distribution.months
        ),
    )
