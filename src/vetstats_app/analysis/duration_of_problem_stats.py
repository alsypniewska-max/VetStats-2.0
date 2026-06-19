from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from vetstats_app.analysis.clinical_common import (
    format_optional_number,
    normalize_ulcer_code,
    resolve_column,
    summarize_duration_values,
)
from vetstats_app.analysis.diagnosis_frequency import DIAGNOSIS_LABELS
from vetstats_app.analysis.report_models import ReportTableBlock

DURATION_OF_PROBLEM_COLUMN = "duration_of_problem"
TYPE_OF_ULCER_COLUMN = "type_of_ulcer"

DURATION_PATTERN = re.compile(
    r"^(?P<number>\d+(?:[.,]\d+)?)\s+(?P<unit>day|days|week|weeks|month|months|year|years)$",
    re.IGNORECASE,
)

UNIT_TO_DAYS: dict[str, float] = {
    "day": 1.0,
    "days": 1.0,
    "week": 7.0,
    "weeks": 7.0,
    "month": 30.4375,
    "months": 30.4375,
    "year": 365.25,
    "years": 365.25,
}


@dataclass(frozen=True)
class UlcerDurationStatsRow:
    ulcer_code: str
    ulcer_label: str
    count: int
    mean_days: float | None
    median_days: float | None
    percentile_25_days: float | None
    percentile_75_days: float | None


@dataclass(frozen=True)
class UlcerDurationValueGroup:
    ulcer_code: str
    ulcer_label: str
    duration_days: tuple[float, ...]


@dataclass(frozen=True)
class DurationOfProblemStatsResult:
    source_label: str
    total_rows: int
    excluded_non_ulcer: int
    excluded_invalid_duration: int
    included_rows: int
    overall_mean_days: float | None
    overall_median_days: float | None
    overall_percentile_25_days: float | None
    overall_percentile_75_days: float | None
    by_ulcer_type: tuple[UlcerDurationStatsRow, ...]
    all_duration_days: tuple[float, ...]
    duration_value_groups: tuple[UlcerDurationValueGroup, ...]
    shortest_ulcer_label: str | None
    longest_ulcer_label: str | None
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def parse_duration_of_problem_days(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower().replace(",", ".")
    if not text or text == "xxx":
        return None
    match = DURATION_PATTERN.match(text)
    if match is None:
        return None
    number = float(match.group("number"))
    unit = match.group("unit").lower()
    multiplier = UNIT_TO_DAYS.get(unit)
    if multiplier is None:
        return None
    return number * multiplier


def compute_duration_of_problem_stats(
    clinical: pd.DataFrame,
    *,
    source_label: str = "clinical",
) -> DurationOfProblemStatsResult:
    ulcer_column = resolve_column(clinical, TYPE_OF_ULCER_COLUMN)
    duration_column = resolve_column(clinical, DURATION_OF_PROBLEM_COLUMN)
    if ulcer_column is None or duration_column is None:
        missing = []
        if ulcer_column is None:
            missing.append(TYPE_OF_ULCER_COLUMN)
        if duration_column is None:
            missing.append(DURATION_OF_PROBLEM_COLUMN)
        return DurationOfProblemStatsResult(
            source_label=source_label,
            total_rows=len(clinical),
            excluded_non_ulcer=len(clinical),
            excluded_invalid_duration=0,
            included_rows=0,
            overall_mean_days=None,
            overall_median_days=None,
            overall_percentile_25_days=None,
            overall_percentile_75_days=None,
            by_ulcer_type=(),
            all_duration_days=(),
            duration_value_groups=(),
            shortest_ulcer_label=None,
            longest_ulcer_label=None,
            error_message=(
                "Brak wymaganych kolumn w tabeli clinical: "
                + ", ".join(missing)
                + "."
            ),
        )

    total_rows = len(clinical)
    ulcer_codes = clinical[ulcer_column].map(normalize_ulcer_code)
    ulcer_mask = ulcer_codes.notna()
    excluded_non_ulcer = int((~ulcer_mask).sum())

    working = clinical.loc[ulcer_mask].copy()
    working["_ulcer_code"] = ulcer_codes[ulcer_mask]
    parsed_days = working[duration_column].map(parse_duration_of_problem_days)
    valid_mask = parsed_days.notna()
    excluded_invalid_duration = int((~valid_mask).sum())
    included = working.loc[valid_mask].copy()
    included["_duration_days"] = parsed_days[valid_mask]

    overall = summarize_duration_values(
        tuple(float(value) for value in included["_duration_days"])
    )

    all_duration_days = tuple(float(value) for value in included["_duration_days"])

    by_ulcer: list[UlcerDurationStatsRow] = []
    duration_value_groups: list[UlcerDurationValueGroup] = []
    for ulcer_code in sorted(included["_ulcer_code"].unique()):
        values = tuple(
            float(value)
            for value in included.loc[
                included["_ulcer_code"] == ulcer_code,
                "_duration_days",
            ]
        )
        stats = summarize_duration_values(values)
        ulcer_label = DIAGNOSIS_LABELS.get(ulcer_code, ulcer_code)
        by_ulcer.append(
            UlcerDurationStatsRow(
                ulcer_code=ulcer_code,
                ulcer_label=ulcer_label,
                count=stats.count,
                mean_days=stats.mean,
                median_days=stats.median,
                percentile_25_days=stats.percentile_25,
                percentile_75_days=stats.percentile_75,
            )
        )
        duration_value_groups.append(
            UlcerDurationValueGroup(
                ulcer_code=ulcer_code,
                ulcer_label=ulcer_label,
                duration_days=values,
            )
        )

    observed = [row for row in by_ulcer if row.count > 0 and row.median_days is not None]
    if observed:
        shortest = min(observed, key=lambda row: (row.median_days, row.ulcer_label))
        longest = max(observed, key=lambda row: (row.median_days, row.ulcer_label))
        shortest_label = shortest.ulcer_label
        longest_label = longest.ulcer_label
    else:
        shortest_label = None
        longest_label = None

    return DurationOfProblemStatsResult(
        source_label=source_label,
        total_rows=total_rows,
        excluded_non_ulcer=excluded_non_ulcer,
        excluded_invalid_duration=excluded_invalid_duration,
        included_rows=overall.count,
        overall_mean_days=overall.mean,
        overall_median_days=overall.median,
        overall_percentile_25_days=overall.percentile_25,
        overall_percentile_75_days=overall.percentile_75,
        by_ulcer_type=tuple(by_ulcer),
        all_duration_days=all_duration_days,
        duration_value_groups=tuple(duration_value_groups),
        shortest_ulcer_label=shortest_label,
        longest_ulcer_label=longest_label,
    )


def build_summary_details(result: DurationOfProblemStatsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przeanalizować duration_of_problem."

    return (
        f"Źródło danych: {result.source_label}. "
        f"Uwzględniono {result.included_rows} z {result.total_rows} wierszy clinical "
        f"z prawidłowym duration_of_problem (wykluczono {result.excluded_non_ulcer} "
        f"nie-wrzodowych oraz {result.excluded_invalid_duration} z nieprawidłową wartością)."
    )


def _compare_mean_to_median(mean: float, median: float) -> str:
    if median <= 0:
        if abs(mean - median) < 1.0:
            return "średnia jest zbliżona do mediany"
        if mean > median:
            return "średnia jest wyższa niż mediana"
        return "średnia jest niższa niż mediana"

    relative_difference = (mean - median) / median
    if abs(relative_difference) < 0.08:
        return "średnia jest zbliżona do mediany"
    if mean > median:
        return "średnia jest wyższa niż mediana"
    return "średnia jest niższa niż mediana"


def _mean_ulcer_extremes(
    rows: tuple[UlcerDurationStatsRow, ...],
) -> tuple[str | None, str | None]:
    observed = [
        row for row in rows if row.count > 0 and row.mean_days is not None
    ]
    if not observed:
        return None, None
    shortest = min(observed, key=lambda row: (row.mean_days, row.ulcer_label))
    longest = max(observed, key=lambda row: (row.mean_days, row.ulcer_label))
    return shortest.ulcer_label, longest.ulcer_label


def _distribution_balance_hint(
    *,
    mean_days: float | None,
    median_days: float | None,
    percentile_25_days: float | None,
    percentile_75_days: float | None,
) -> str:
    if mean_days is None or median_days is None:
        return (
            "Brak wystarczających danych do oceny kształtu rozkładu czasu trwania problemu."
        )

    if median_days > 0 and mean_days > median_days * 1.12:
        return (
            "Średnia wyraźnie przewyższa medianę, co sugeruje przypadki z dłuższym "
            "czasem trwania i prawoskośny rozkład."
        )
    if median_days > 0 and mean_days < median_days * 0.88:
        return (
            "Średnia jest wyraźnie niższa od mediany, co może wskazywać na grupę "
            "krótszych przypadków odchylających rozkład."
        )

    if (
        percentile_25_days is not None
        and percentile_75_days is not None
        and median_days > 0
        and (percentile_75_days - percentile_25_days) > median_days * 0.75
    ):
        return (
            "Duży rozstęp między kwartylami wskazuje na zróżnicowany czas trwania "
            "problemów w badanej grupie."
        )

    return (
        "Średnia i mediana są do siebie zbliżone, a rozkład wydaje się stosunkowo "
        "wyrównany."
    )


def _ulcer_types_with_higher_mean_than_median(
    rows: tuple[UlcerDurationStatsRow, ...],
    *,
    threshold_ratio: float = 0.12,
) -> tuple[str, ...]:
    notable: list[str] = []
    for row in rows:
        if (
            row.count == 0
            or row.mean_days is None
            or row.median_days is None
            or row.median_days <= 0
        ):
            continue
        if row.mean_days > row.median_days * (1.0 + threshold_ratio):
            notable.append(row.ulcer_label)
    return tuple(notable)


def build_interpretation_summary(result: DurationOfProblemStatsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przygotować interpretacji."

    if result.included_rows == 0:
        return "Brak przypadków z prawidłowym czasem trwania problemu przed wizytą."

    parts = [
        (
            f"Łącznie przeanalizowano {result.included_rows} przypadków wrzodowych. "
            f"Mediana czasu trwania problemu przed pierwszą wizytą: "
            f"{format_optional_number(result.overall_median_days)} dni."
        ),
        (
            f"Średnia czasu trwania problemu: "
            f"{format_optional_number(result.overall_mean_days)} dni."
        ),
    ]

    if result.overall_mean_days is not None and result.overall_median_days is not None:
        parts.append(
            "Ogólnie "
            + _compare_mean_to_median(
                result.overall_mean_days,
                result.overall_median_days,
            )
            + "."
        )

    if result.shortest_ulcer_label and result.longest_ulcer_label:
        parts.append(
            f"Najkrótszy medianowy czas: {result.shortest_ulcer_label}. "
            f"Najdłuższy medianowy czas: {result.longest_ulcer_label}."
        )

    shortest_mean_label, longest_mean_label = _mean_ulcer_extremes(result.by_ulcer_type)
    if shortest_mean_label and longest_mean_label:
        parts.append(
            f"Najkrótszy średni czas: {shortest_mean_label}. "
            f"Najdłuższy średni czas: {longest_mean_label}."
        )

    parts.append(
        _distribution_balance_hint(
            mean_days=result.overall_mean_days,
            median_days=result.overall_median_days,
            percentile_25_days=result.overall_percentile_25_days,
            percentile_75_days=result.overall_percentile_75_days,
        )
    )

    notable_ulcer_types = _ulcer_types_with_higher_mean_than_median(result.by_ulcer_type)
    if notable_ulcer_types:
        joined_labels = ", ".join(notable_ulcer_types)
        parts.append(
            f"Dla typów wrzodu: {joined_labels} średnia przewyższa medianę, "
            f"co może wskazywać na wpływ pojedynczych dłuższych przypadków."
        )

    return " ".join(parts)


def build_descriptive_stats_block(
    result: DurationOfProblemStatsResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba wierszy clinical (N)", str(result.total_rows)),
            ("Wykluczone — nie wrzód (n)", str(result.excluded_non_ulcer)),
            (
                "Wykluczone — nieprawidłowe duration_of_problem (n)",
                str(result.excluded_invalid_duration),
            ),
            ("Uwzględnione (n)", str(result.included_rows)),
            ("Średnia (dni)", format_optional_number(result.overall_mean_days)),
            ("Mediana (dni)", format_optional_number(result.overall_median_days)),
            ("Percentyl 25 (dni)", format_optional_number(result.overall_percentile_25_days)),
            ("Percentyl 75 (dni)", format_optional_number(result.overall_percentile_75_days)),
            ("Najkrótszy typ wrzodu (mediana)", result.shortest_ulcer_label or "—"),
            ("Najdłuższy typ wrzodu (mediana)", result.longest_ulcer_label or "—"),
        ),
    )
