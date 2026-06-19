from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from vetstats_app.analysis.clinical_common import (
    build_patient_species_breed_lookup,
    classify_species,
    format_optional_number,
    normalize_breed,
    normalize_ems,
    normalize_farmacology_surgery,
    normalize_ulcer_code,
    resolve_column,
    summarize_duration_values_extended,
)
from vetstats_app.analysis.diagnosis_frequency import DIAGNOSIS_LABELS
from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.analysis.treatment_cases import (
    TreatmentCaseExclusionSummary,
    enumerate_treatment_cases,
    filter_healed_cases_with_duration,
)
from vetstats_app.analysis.treatment_groups import FARMACOLOGY_SURGERY_COLUMNS

MIN_DISPLAY_GROUP_SIZE = 3
MIN_TEST_GROUP_SIZE = 5
TOP_DOG_BREED_CHART_LIMIT = 8

EMS_LABELS = {
    "yes": "EMS tak",
    "no": "EMS nie",
}

SPECIES_LABELS = {
    "dog": "Psy",
    "cat": "Koty",
}

FARMACOLOGY_TREATMENT_LABELS = {
    "f": "Tylko farmakologia",
    "s": "Farmakologia + zabieg",
}


@dataclass(frozen=True)
class EmsTreatmentDurationExclusions:
    total_clinical_rows: int
    excluded_non_ulcer: int
    excluded_not_good: int
    excluded_enucleation: int
    excluded_no_followup: int
    excluded_continuation: int
    excluded_duration_unavailable: int
    included_healed_with_duration: int
    excluded_non_pharmacological: int
    excluded_invalid_ems: int
    excluded_invalid_ulcer: int
    excluded_unknown_species: int
    excluded_unknown_breed: int
    included_pharmacological_ems_cases: int
    included_ems_yes: int
    included_ems_no: int


@dataclass(frozen=True)
class DurationStatsRow:
    group_label: str
    count: int
    mean_days: float | None
    median_days: float | None
    min_days: float | None
    max_days: float | None
    percentile_25_days: float | None
    percentile_75_days: float | None


@dataclass(frozen=True)
class EmsComparisonRow:
    context_label: str
    ems_yes: DurationStatsRow | None
    ems_no: DurationStatsRow | None


@dataclass(frozen=True)
class EmsUlcerComparisonRow:
    ulcer_code: str
    ulcer_label: str
    ems_yes: DurationStatsRow | None
    ems_no: DurationStatsRow | None


@dataclass(frozen=True)
class EmsBreedComparisonRow:
    breed_label: str
    ems_yes: DurationStatsRow | None
    ems_no: DurationStatsRow | None


@dataclass(frozen=True)
class EmsDurationValueGroup:
    group_label: str
    duration_days: tuple[float, ...]


@dataclass(frozen=True)
class EmsUlcerGroupedBarRow:
    ulcer_label: str
    ems_yes_median: float | None
    ems_no_median: float | None


@dataclass(frozen=True)
class StatisticalTestRow:
    comparison_label: str
    test_name: str
    raw_p_value: str
    corrected_p_value: str
    median_difference_days: str
    direction: str
    note: str
    raw_p_value_float: float | None = None


@dataclass(frozen=True)
class UlcerSurgeryRateExclusions:
    excluded_non_ulcer_rows: int
    excluded_invalid_ulcer_cases: int
    excluded_invalid_farmacology_cases: int
    excluded_unknown_species_cases: int
    included_broader_cases: int


@dataclass(frozen=True)
class SurgeryRateSummaryRow:
    context_label: str
    total_cases: int
    pharmacology_only_count: int
    surgery_count: int
    pharmacology_only_percent: float | None
    surgery_percent: float | None


@dataclass(frozen=True)
class UlcerSurgeryRateRow:
    ulcer_code: str
    ulcer_label: str
    total_cases: int
    pharmacology_only_count: int
    surgery_count: int
    surgery_percent: float | None


@dataclass(frozen=True)
class UlcerSurgeryRateBlock:
    exclusions: UlcerSurgeryRateExclusions
    overall_summary: SurgeryRateSummaryRow | None
    dog_summary: SurgeryRateSummaryRow | None
    cat_summary: SurgeryRateSummaryRow | None
    ulcer_type_rows: tuple[UlcerSurgeryRateRow, ...]


@dataclass(frozen=True)
class EmsTreatmentDurationResult:
    source_clinical_label: str
    source_patient_label: str
    exclusions: EmsTreatmentDurationExclusions
    overall_comparison: EmsComparisonRow | None
    ulcer_comparisons: tuple[EmsUlcerComparisonRow, ...]
    dog_overall_comparison: EmsComparisonRow | None
    cat_overall_comparison: EmsComparisonRow | None
    dog_ulcer_comparisons: tuple[EmsUlcerComparisonRow, ...]
    cat_ulcer_comparisons: tuple[EmsUlcerComparisonRow, ...]
    dog_breed_comparisons: tuple[EmsBreedComparisonRow, ...]
    statistical_tests: tuple[StatisticalTestRow, ...]
    overall_ems_value_groups: tuple[EmsDurationValueGroup, ...]
    dog_ems_value_groups: tuple[EmsDurationValueGroup, ...]
    cat_ems_value_groups: tuple[EmsDurationValueGroup, ...]
    pooled_ulcer_grouped_bars: tuple[EmsUlcerGroupedBarRow, ...]
    dog_ulcer_grouped_bars: tuple[EmsUlcerGroupedBarRow, ...]
    cat_ulcer_grouped_bars: tuple[EmsUlcerGroupedBarRow, ...]
    dog_breed_ems_value_groups: tuple[EmsDurationValueGroup, ...]
    surgery_rate: UlcerSurgeryRateBlock
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


@dataclass(frozen=True)
class _EmsCase:
    duration_days: int
    ems: str
    ulcer_code: str
    ulcer_label: str
    species: str | None
    breed: str | None


@dataclass(frozen=True)
class _BroaderUlcerCase:
    farmacology: str
    ulcer_code: str
    ulcer_label: str
    species: str | None


def _ulcer_label(ulcer_code: str) -> str:
    return DIAGNOSIS_LABELS.get(ulcer_code, ulcer_code)


def _stats_row(label: str, values: tuple[float, ...]) -> DurationStatsRow | None:
    if len(values) < MIN_DISPLAY_GROUP_SIZE:
        return None
    stats = summarize_duration_values_extended(values)
    if stats.count == 0:
        return None
    return DurationStatsRow(
        group_label=label,
        count=stats.count,
        mean_days=stats.mean_days,
        median_days=stats.median_days,
        min_days=stats.min_days,
        max_days=stats.max_days,
        percentile_25_days=stats.percentile_25_days,
        percentile_75_days=stats.percentile_75_days,
    )


def _split_ems_values(
    cases: tuple[_EmsCase, ...],
    *,
    species: str | None = None,
    ulcer_code: str | None = None,
    breed: str | None = None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    yes_values: list[float] = []
    no_values: list[float] = []
    for case in cases:
        if species is not None and case.species != species:
            continue
        if ulcer_code is not None and case.ulcer_code != ulcer_code:
            continue
        if breed is not None and case.breed != breed:
            continue
        if case.ems == "yes":
            yes_values.append(float(case.duration_days))
        else:
            no_values.append(float(case.duration_days))
    return tuple(yes_values), tuple(no_values)


def _median_difference_and_direction(
    yes_values: tuple[float, ...],
    no_values: tuple[float, ...],
) -> tuple[float | None, str]:
    yes_stats = summarize_duration_values_extended(yes_values)
    no_stats = summarize_duration_values_extended(no_values)
    if yes_stats.median_days is None or no_stats.median_days is None:
        return None, "brak wyraźnej różnicy"
    difference = yes_stats.median_days - no_stats.median_days
    if difference < 0:
        return difference, "krótszy czas przy EMS"
    if difference > 0:
        return difference, "dłuższy czas przy EMS"
    return difference, "brak wyraźnej różnicy"


def _mann_whitney_test(
    *,
    comparison_label: str,
    yes_values: tuple[float, ...],
    no_values: tuple[float, ...],
) -> StatisticalTestRow:
    median_diff, direction = _median_difference_and_direction(yes_values, no_values)
    median_diff_text = (
        format_optional_number(median_diff) if median_diff is not None else "—"
    )
    if (
        len(yes_values) < MIN_TEST_GROUP_SIZE
        or len(no_values) < MIN_TEST_GROUP_SIZE
    ):
        return StatisticalTestRow(
            comparison_label=comparison_label,
            test_name="Mann–Whitney U",
            raw_p_value="—",
            corrected_p_value="—",
            median_difference_days=median_diff_text,
            direction=direction,
            note="test niedostępny (za mała liczba przypadków)",
        )
    try:
        from scipy.stats import mannwhitneyu

        _, p_value = mannwhitneyu(yes_values, no_values, alternative="two-sided")
        return StatisticalTestRow(
            comparison_label=comparison_label,
            test_name="Mann–Whitney U",
            raw_p_value=f"{p_value:.4f}",
            corrected_p_value="—",
            median_difference_days=median_diff_text,
            direction=direction,
            note="",
            raw_p_value_float=p_value,
        )
    except Exception:
        return StatisticalTestRow(
            comparison_label=comparison_label,
            test_name="Mann–Whitney U",
            raw_p_value="—",
            corrected_p_value="—",
            median_difference_days=median_diff_text,
            direction=direction,
            note="test niedostępny (błąd obliczeń)",
        )


def _apply_benjamini_hochberg(
    tests: list[StatisticalTestRow],
    indices: list[int],
) -> list[StatisticalTestRow]:
    eligible = [
        (index, tests[index].raw_p_value_float)
        for index in indices
        if tests[index].raw_p_value_float is not None
    ]
    if not eligible:
        return tests

    eligible.sort(key=lambda item: item[1])
    m = len(eligible)
    corrected: dict[int, float] = {}
    prev = 1.0
    for rank in range(m, 0, -1):
        index, p_value = eligible[rank - 1]
        value = min(prev, p_value * m / rank)
        corrected[index] = value
        prev = value

    updated = list(tests)
    for index, value in corrected.items():
        row = updated[index]
        updated[index] = StatisticalTestRow(
            comparison_label=row.comparison_label,
            test_name=row.test_name,
            raw_p_value=row.raw_p_value,
            corrected_p_value=f"{value:.4f}",
            median_difference_days=row.median_difference_days,
            direction=row.direction,
            note=row.note,
            raw_p_value_float=row.raw_p_value_float,
        )
    return updated


def _comparison_row(
    cases: tuple[_EmsCase, ...],
    *,
    context_label: str,
    species: str | None = None,
    ulcer_code: str | None = None,
) -> EmsComparisonRow:
    yes_values, no_values = _split_ems_values(
        cases,
        species=species,
        ulcer_code=ulcer_code,
    )
    return EmsComparisonRow(
        context_label=context_label,
        ems_yes=_stats_row(EMS_LABELS["yes"], yes_values),
        ems_no=_stats_row(EMS_LABELS["no"], no_values),
    )


def _ulcer_comparisons(
    cases: tuple[_EmsCase, ...],
    *,
    species: str | None = None,
) -> tuple[EmsUlcerComparisonRow, ...]:
    ulcer_codes = sorted(
        {
            case.ulcer_code
            for case in cases
            if species is None or case.species == species
        }
    )
    rows: list[EmsUlcerComparisonRow] = []
    for ulcer_code in ulcer_codes:
        yes_values, no_values = _split_ems_values(
            cases,
            species=species,
            ulcer_code=ulcer_code,
        )
        if (
            len(yes_values) < MIN_DISPLAY_GROUP_SIZE
            and len(no_values) < MIN_DISPLAY_GROUP_SIZE
        ):
            continue
        rows.append(
            EmsUlcerComparisonRow(
                ulcer_code=ulcer_code,
                ulcer_label=_ulcer_label(ulcer_code),
                ems_yes=_stats_row(EMS_LABELS["yes"], yes_values),
                ems_no=_stats_row(EMS_LABELS["no"], no_values),
            )
        )
    rows.sort(key=lambda row: (-_row_total_count(row), row.ulcer_label))
    return tuple(rows)


def _row_total_count(row: EmsUlcerComparisonRow) -> int:
    total = 0
    if row.ems_yes is not None:
        total += row.ems_yes.count
    if row.ems_no is not None:
        total += row.ems_no.count
    return total


def _breed_comparisons(
    cases: tuple[_EmsCase, ...],
) -> tuple[EmsBreedComparisonRow, ...]:
    breeds = sorted(
        {
            case.breed
            for case in cases
            if case.species == "dog" and case.breed is not None
        }
    )
    rows: list[EmsBreedComparisonRow] = []
    for breed in breeds:
        yes_values, no_values = _split_ems_values(
            cases,
            species="dog",
            breed=breed,
        )
        if (
            len(yes_values) < MIN_DISPLAY_GROUP_SIZE
            and len(no_values) < MIN_DISPLAY_GROUP_SIZE
        ):
            continue
        rows.append(
            EmsBreedComparisonRow(
                breed_label=breed,
                ems_yes=_stats_row(EMS_LABELS["yes"], yes_values),
                ems_no=_stats_row(EMS_LABELS["no"], no_values),
            )
        )
    rows.sort(
        key=lambda row: (
            -(
                (row.ems_yes.count if row.ems_yes else 0)
                + (row.ems_no.count if row.ems_no else 0)
            ),
            row.breed_label,
        )
    )
    return tuple(rows)


def _ems_value_groups(
    cases: tuple[_EmsCase, ...],
    *,
    species: str | None = None,
) -> tuple[EmsDurationValueGroup, ...]:
    yes_values, no_values = _split_ems_values(cases, species=species)
    groups: list[EmsDurationValueGroup] = []
    if len(yes_values) >= MIN_DISPLAY_GROUP_SIZE:
        groups.append(
            EmsDurationValueGroup(
                group_label=EMS_LABELS["yes"],
                duration_days=yes_values,
            )
        )
    if len(no_values) >= MIN_DISPLAY_GROUP_SIZE:
        groups.append(
            EmsDurationValueGroup(
                group_label=EMS_LABELS["no"],
                duration_days=no_values,
            )
        )
    return tuple(groups)


def _ulcer_grouped_bars(
    comparisons: tuple[EmsUlcerComparisonRow, ...],
) -> tuple[EmsUlcerGroupedBarRow, ...]:
    rows: list[EmsUlcerGroupedBarRow] = []
    for comparison in comparisons:
        if comparison.ems_yes is None and comparison.ems_no is None:
            continue
        rows.append(
            EmsUlcerGroupedBarRow(
                ulcer_label=comparison.ulcer_label,
                ems_yes_median=(
                    comparison.ems_yes.median_days if comparison.ems_yes else None
                ),
                ems_no_median=(
                    comparison.ems_no.median_days if comparison.ems_no else None
                ),
            )
        )
    return tuple(rows)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}%"


def _empty_surgery_rate_block() -> UlcerSurgeryRateBlock:
    return UlcerSurgeryRateBlock(
        exclusions=UlcerSurgeryRateExclusions(
            excluded_non_ulcer_rows=0,
            excluded_invalid_ulcer_cases=0,
            excluded_invalid_farmacology_cases=0,
            excluded_unknown_species_cases=0,
            included_broader_cases=0,
        ),
        overall_summary=None,
        dog_summary=None,
        cat_summary=None,
        ulcer_type_rows=(),
    )


def _surgery_rate_summary(
    cases: tuple[_BroaderUlcerCase, ...],
    *,
    context_label: str,
    species: str | None = None,
) -> SurgeryRateSummaryRow | None:
    filtered = tuple(
        case
        for case in cases
        if species is None or case.species == species
    )
    if not filtered:
        return None
    pharmacology_only_count = sum(
        1 for case in filtered if case.farmacology == "f"
    )
    surgery_count = sum(1 for case in filtered if case.farmacology == "s")
    total_cases = len(filtered)
    return SurgeryRateSummaryRow(
        context_label=context_label,
        total_cases=total_cases,
        pharmacology_only_count=pharmacology_only_count,
        surgery_count=surgery_count,
        pharmacology_only_percent=(
            pharmacology_only_count / total_cases * 100.0 if total_cases else None
        ),
        surgery_percent=(
            surgery_count / total_cases * 100.0 if total_cases else None
        ),
    )


def _ulcer_surgery_rate_rows(
    cases: tuple[_BroaderUlcerCase, ...],
) -> tuple[UlcerSurgeryRateRow, ...]:
    ulcer_codes = sorted({case.ulcer_code for case in cases})
    rows: list[UlcerSurgeryRateRow] = []
    for ulcer_code in ulcer_codes:
        subset = tuple(case for case in cases if case.ulcer_code == ulcer_code)
        if len(subset) < MIN_DISPLAY_GROUP_SIZE:
            continue
        pharmacology_only_count = sum(
            1 for case in subset if case.farmacology == "f"
        )
        surgery_count = sum(1 for case in subset if case.farmacology == "s")
        total_cases = len(subset)
        rows.append(
            UlcerSurgeryRateRow(
                ulcer_code=ulcer_code,
                ulcer_label=_ulcer_label(ulcer_code),
                total_cases=total_cases,
                pharmacology_only_count=pharmacology_only_count,
                surgery_count=surgery_count,
                surgery_percent=(
                    surgery_count / total_cases * 100.0 if total_cases else None
                ),
            )
        )
    rows.sort(key=lambda row: (-row.total_cases, row.ulcer_label))
    return tuple(rows)


def _build_surgery_rate_block(
    clinical: pd.DataFrame,
    patient_lookup: dict[str, tuple[object, object]],
    farmacology_col: str,
) -> UlcerSurgeryRateBlock:
    ulcer_col = resolve_column(clinical, "type_of_ulcer")
    if ulcer_col is None:
        return _empty_surgery_rate_block()

    ulcer_mask = clinical[ulcer_col].map(normalize_ulcer_code).notna()
    excluded_non_ulcer_rows = int((~ulcer_mask).sum())
    ulcer_frame = clinical.loc[ulcer_mask]
    cases = enumerate_treatment_cases(ulcer_frame)

    excluded_invalid_ulcer = 0
    excluded_invalid_farmacology = 0
    excluded_unknown_species = 0
    broader_cases: list[_BroaderUlcerCase] = []

    for case in cases:
        ulcer_code = normalize_ulcer_code(case.terminal_ulcer_code)
        if ulcer_code is None:
            excluded_invalid_ulcer += 1
            continue

        terminal_row = clinical.loc[case.terminal_row_index]
        farmacology = normalize_farmacology_surgery(terminal_row[farmacology_col])
        if farmacology not in ("f", "s"):
            excluded_invalid_farmacology += 1
            continue

        species_value, _ = patient_lookup.get(case.patient_id, (None, None))
        species = classify_species(species_value)
        if species is None:
            excluded_unknown_species += 1

        broader_cases.append(
            _BroaderUlcerCase(
                farmacology=farmacology,
                ulcer_code=ulcer_code,
                ulcer_label=_ulcer_label(ulcer_code),
                species=species,
            )
        )

    cases_tuple = tuple(broader_cases)
    return UlcerSurgeryRateBlock(
        exclusions=UlcerSurgeryRateExclusions(
            excluded_non_ulcer_rows=excluded_non_ulcer_rows,
            excluded_invalid_ulcer_cases=excluded_invalid_ulcer,
            excluded_invalid_farmacology_cases=excluded_invalid_farmacology,
            excluded_unknown_species_cases=excluded_unknown_species,
            included_broader_cases=len(cases_tuple),
        ),
        overall_summary=_surgery_rate_summary(
            cases_tuple,
            context_label="Łącznie (psy i koty)",
        ),
        dog_summary=_surgery_rate_summary(
            cases_tuple,
            context_label="Psy",
            species="dog",
        ),
        cat_summary=_surgery_rate_summary(
            cases_tuple,
            context_label="Koty",
            species="cat",
        ),
        ulcer_type_rows=_ulcer_surgery_rate_rows(cases_tuple),
    )


def _resolve_terminal_columns(clinical: pd.DataFrame) -> dict[str, str | None]:
    farmacology_col = None
    for candidate in FARMACOLOGY_SURGERY_COLUMNS:
        farmacology_col = resolve_column(clinical, candidate)
        if farmacology_col is not None:
            break
    return {
        "ems": resolve_column(clinical, "EMS"),
        "farmacology": farmacology_col,
    }


def _build_exclusions(
    case_summary: TreatmentCaseExclusionSummary,
    *,
    excluded_non_pharmacological: int,
    excluded_invalid_ems: int,
    excluded_invalid_ulcer: int,
    excluded_unknown_species: int,
    excluded_unknown_breed: int,
    included_pharmacological_ems_cases: int,
    included_ems_yes: int,
    included_ems_no: int,
) -> EmsTreatmentDurationExclusions:
    return EmsTreatmentDurationExclusions(
        total_clinical_rows=case_summary.total_clinical_rows,
        excluded_non_ulcer=case_summary.excluded_non_ulcer,
        excluded_not_good=case_summary.excluded_not_good,
        excluded_enucleation=case_summary.excluded_enucleation,
        excluded_no_followup=case_summary.excluded_no_followup,
        excluded_continuation=case_summary.excluded_continuation,
        excluded_duration_unavailable=case_summary.excluded_duration_unavailable,
        included_healed_with_duration=case_summary.included_healed_with_duration,
        excluded_non_pharmacological=excluded_non_pharmacological,
        excluded_invalid_ems=excluded_invalid_ems,
        excluded_invalid_ulcer=excluded_invalid_ulcer,
        excluded_unknown_species=excluded_unknown_species,
        excluded_unknown_breed=excluded_unknown_breed,
        included_pharmacological_ems_cases=included_pharmacological_ems_cases,
        included_ems_yes=included_ems_yes,
        included_ems_no=included_ems_no,
    )


def compute_ems_treatment_duration(
    clinical: pd.DataFrame,
    patient: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_patient_label: str = "patient",
) -> EmsTreatmentDurationResult:
    from data_sterilizer.schemas.patient import PATIENT_ID_COLUMN

    patient_id_col = resolve_column(patient, PATIENT_ID_COLUMN)
    if patient_id_col is None:
        empty_case_summary = TreatmentCaseExclusionSummary(
            total_clinical_rows=len(clinical),
            excluded_non_ulcer=0,
            excluded_not_good=0,
            excluded_enucleation=0,
            excluded_no_followup=0,
            excluded_continuation=0,
            excluded_duration_unavailable=0,
            included_healed_with_duration=0,
        )
        return EmsTreatmentDurationResult(
            source_clinical_label=source_clinical_label,
            source_patient_label=source_patient_label,
            exclusions=_build_exclusions(
                empty_case_summary,
                excluded_non_pharmacological=0,
                excluded_invalid_ems=0,
                excluded_invalid_ulcer=0,
                excluded_unknown_species=0,
                excluded_unknown_breed=0,
                included_pharmacological_ems_cases=0,
                included_ems_yes=0,
                included_ems_no=0,
            ),
            overall_comparison=None,
            ulcer_comparisons=(),
            dog_overall_comparison=None,
            cat_overall_comparison=None,
            dog_ulcer_comparisons=(),
            cat_ulcer_comparisons=(),
            dog_breed_comparisons=(),
            statistical_tests=(),
            overall_ems_value_groups=(),
            dog_ems_value_groups=(),
            cat_ems_value_groups=(),
            pooled_ulcer_grouped_bars=(),
            dog_ulcer_grouped_bars=(),
            cat_ulcer_grouped_bars=(),
            dog_breed_ems_value_groups=(),
            surgery_rate=_empty_surgery_rate_block(),
            error_message="Brak kolumny patient_ID w tabeli patient.",
        )

    terminal_columns = _resolve_terminal_columns(clinical)
    if terminal_columns["ems"] is None or terminal_columns["farmacology"] is None:
        missing = []
        if terminal_columns["ems"] is None:
            missing.append("EMS")
        if terminal_columns["farmacology"] is None:
            missing.append("farmacology_surgery")
        empty_case_summary = TreatmentCaseExclusionSummary(
            total_clinical_rows=len(clinical),
            excluded_non_ulcer=0,
            excluded_not_good=0,
            excluded_enucleation=0,
            excluded_no_followup=0,
            excluded_continuation=0,
            excluded_duration_unavailable=0,
            included_healed_with_duration=0,
        )
        return EmsTreatmentDurationResult(
            source_clinical_label=source_clinical_label,
            source_patient_label=source_patient_label,
            exclusions=_build_exclusions(
                empty_case_summary,
                excluded_non_pharmacological=0,
                excluded_invalid_ems=0,
                excluded_invalid_ulcer=0,
                excluded_unknown_species=0,
                excluded_unknown_breed=0,
                included_pharmacological_ems_cases=0,
                included_ems_yes=0,
                included_ems_no=0,
            ),
            overall_comparison=None,
            ulcer_comparisons=(),
            dog_overall_comparison=None,
            cat_overall_comparison=None,
            dog_ulcer_comparisons=(),
            cat_ulcer_comparisons=(),
            dog_breed_comparisons=(),
            statistical_tests=(),
            overall_ems_value_groups=(),
            dog_ems_value_groups=(),
            cat_ems_value_groups=(),
            pooled_ulcer_grouped_bars=(),
            dog_ulcer_grouped_bars=(),
            cat_ulcer_grouped_bars=(),
            dog_breed_ems_value_groups=(),
            surgery_rate=_empty_surgery_rate_block(),
            error_message=f"Brak kolumn w tabeli clinical: {', '.join(missing)}.",
        )

    healed_cases, case_summary = filter_healed_cases_with_duration(clinical)
    lookup = build_patient_species_breed_lookup(patient)
    ems_col = terminal_columns["ems"]
    farmacology_col = terminal_columns["farmacology"]

    excluded_non_pharmacological = 0
    excluded_invalid_ems = 0
    excluded_invalid_ulcer = 0
    excluded_unknown_species = 0
    excluded_unknown_breed = 0
    enriched_cases: list[_EmsCase] = []

    for case in healed_cases:
        terminal_row = clinical.loc[case.terminal_row_index]
        if normalize_farmacology_surgery(terminal_row[farmacology_col]) != "f":
            excluded_non_pharmacological += 1
            continue

        ems = normalize_ems(terminal_row[ems_col])
        if ems is None:
            excluded_invalid_ems += 1
            continue

        ulcer_code = normalize_ulcer_code(case.terminal_ulcer_code)
        if ulcer_code is None:
            excluded_invalid_ulcer += 1
            continue

        species_value, breed_value = lookup.get(case.patient_id, (None, None))
        species = classify_species(species_value)
        if species is None:
            excluded_unknown_species += 1
        breed = normalize_breed(breed_value)
        if species == "dog" and breed is None:
            excluded_unknown_breed += 1

        enriched_cases.append(
            _EmsCase(
                duration_days=case.duration_days,
                ems=ems,
                ulcer_code=ulcer_code,
                ulcer_label=_ulcer_label(ulcer_code),
                species=species,
                breed=breed if species == "dog" else None,
            )
        )

    cases_tuple = tuple(enriched_cases)
    included_ems_yes = sum(1 for case in cases_tuple if case.ems == "yes")
    included_ems_no = sum(1 for case in cases_tuple if case.ems == "no")

    exclusions = _build_exclusions(
        case_summary,
        excluded_non_pharmacological=excluded_non_pharmacological,
        excluded_invalid_ems=excluded_invalid_ems,
        excluded_invalid_ulcer=excluded_invalid_ulcer,
        excluded_unknown_species=excluded_unknown_species,
        excluded_unknown_breed=excluded_unknown_breed,
        included_pharmacological_ems_cases=len(cases_tuple),
        included_ems_yes=included_ems_yes,
        included_ems_no=included_ems_no,
    )

    overall_comparison = _comparison_row(
        cases_tuple,
        context_label="Łącznie (psy i koty)",
    )
    ulcer_comparisons = _ulcer_comparisons(cases_tuple)
    dog_overall_comparison = _comparison_row(
        cases_tuple,
        context_label="Psy",
        species="dog",
    )
    cat_overall_comparison = _comparison_row(
        cases_tuple,
        context_label="Koty",
        species="cat",
    )
    dog_ulcer_comparisons = _ulcer_comparisons(cases_tuple, species="dog")
    cat_ulcer_comparisons = _ulcer_comparisons(cases_tuple, species="cat")
    dog_breed_comparisons = _breed_comparisons(cases_tuple)

    tests: list[StatisticalTestRow] = []
    ulcer_test_indices: list[int] = []
    dog_ulcer_test_indices: list[int] = []
    cat_ulcer_test_indices: list[int] = []

    yes_values, no_values = _split_ems_values(cases_tuple)
    tests.append(
        _mann_whitney_test(
            comparison_label="Łącznie — EMS tak vs EMS nie",
            yes_values=yes_values,
            no_values=no_values,
        )
    )

    for comparison in ulcer_comparisons:
        yes_values, no_values = _split_ems_values(
            cases_tuple,
            ulcer_code=comparison.ulcer_code,
        )
        tests.append(
            _mann_whitney_test(
                comparison_label=(
                    f"Łącznie — {comparison.ulcer_label}: EMS tak vs EMS nie"
                ),
                yes_values=yes_values,
                no_values=no_values,
            )
        )
        ulcer_test_indices.append(len(tests) - 1)

    dog_yes, dog_no = _split_ems_values(cases_tuple, species="dog")
    tests.append(
        _mann_whitney_test(
            comparison_label="Psy — EMS tak vs EMS nie",
            yes_values=dog_yes,
            no_values=dog_no,
        )
    )
    for comparison in dog_ulcer_comparisons:
        yes_values, no_values = _split_ems_values(
            cases_tuple,
            species="dog",
            ulcer_code=comparison.ulcer_code,
        )
        tests.append(
            _mann_whitney_test(
                comparison_label=(
                    f"Psy — {comparison.ulcer_label}: EMS tak vs EMS nie"
                ),
                yes_values=yes_values,
                no_values=no_values,
            )
        )
        dog_ulcer_test_indices.append(len(tests) - 1)

    cat_yes, cat_no = _split_ems_values(cases_tuple, species="cat")
    tests.append(
        _mann_whitney_test(
            comparison_label="Koty — EMS tak vs EMS nie",
            yes_values=cat_yes,
            no_values=cat_no,
        )
    )
    for comparison in cat_ulcer_comparisons:
        yes_values, no_values = _split_ems_values(
            cases_tuple,
            species="cat",
            ulcer_code=comparison.ulcer_code,
        )
        tests.append(
            _mann_whitney_test(
                comparison_label=(
                    f"Koty — {comparison.ulcer_label}: EMS tak vs EMS nie"
                ),
                yes_values=yes_values,
                no_values=no_values,
            )
        )
        cat_ulcer_test_indices.append(len(tests) - 1)

    for comparison in dog_breed_comparisons:
        yes_values, no_values = _split_ems_values(
            cases_tuple,
            species="dog",
            breed=comparison.breed_label,
        )
        tests.append(
            _mann_whitney_test(
                comparison_label=(
                    f"Psy — rasa {comparison.breed_label}: EMS tak vs EMS nie"
                ),
                yes_values=yes_values,
                no_values=no_values,
            )
        )

    tests = _apply_benjamini_hochberg(tests, ulcer_test_indices)
    tests = _apply_benjamini_hochberg(tests, dog_ulcer_test_indices)
    tests = _apply_benjamini_hochberg(tests, cat_ulcer_test_indices)

    dog_breed_value_groups: list[EmsDurationValueGroup] = []
    for comparison in dog_breed_comparisons[:TOP_DOG_BREED_CHART_LIMIT]:
        yes_values, no_values = _split_ems_values(
            cases_tuple,
            species="dog",
            breed=comparison.breed_label,
        )
        if len(yes_values) >= MIN_DISPLAY_GROUP_SIZE:
            dog_breed_value_groups.append(
                EmsDurationValueGroup(
                    group_label=f"{comparison.breed_label} — {EMS_LABELS['yes']}",
                    duration_days=yes_values,
                )
            )
        if len(no_values) >= MIN_DISPLAY_GROUP_SIZE:
            dog_breed_value_groups.append(
                EmsDurationValueGroup(
                    group_label=f"{comparison.breed_label} — {EMS_LABELS['no']}",
                    duration_days=no_values,
                )
            )

    return EmsTreatmentDurationResult(
        source_clinical_label=source_clinical_label,
        source_patient_label=source_patient_label,
        exclusions=exclusions,
        overall_comparison=overall_comparison,
        ulcer_comparisons=ulcer_comparisons,
        dog_overall_comparison=dog_overall_comparison,
        cat_overall_comparison=cat_overall_comparison,
        dog_ulcer_comparisons=dog_ulcer_comparisons,
        cat_ulcer_comparisons=cat_ulcer_comparisons,
        dog_breed_comparisons=dog_breed_comparisons,
        statistical_tests=tuple(tests),
        overall_ems_value_groups=_ems_value_groups(cases_tuple),
        dog_ems_value_groups=_ems_value_groups(cases_tuple, species="dog"),
        cat_ems_value_groups=_ems_value_groups(cases_tuple, species="cat"),
        pooled_ulcer_grouped_bars=_ulcer_grouped_bars(ulcer_comparisons),
        dog_ulcer_grouped_bars=_ulcer_grouped_bars(dog_ulcer_comparisons),
        cat_ulcer_grouped_bars=_ulcer_grouped_bars(cat_ulcer_comparisons),
        dog_breed_ems_value_groups=tuple(dog_breed_value_groups),
        surgery_rate=_build_surgery_rate_block(clinical, lookup, farmacology_col),
    )


def _duration_cells(row: DurationStatsRow | None) -> tuple[str, ...]:
    if row is None:
        return ("—", "—", "—", "—", "—", "—", "—")
    return (
        str(row.count),
        format_optional_number(row.mean_days),
        format_optional_number(row.median_days),
        format_optional_number(row.min_days),
        format_optional_number(row.max_days),
        format_optional_number(row.percentile_25_days),
        format_optional_number(row.percentile_75_days),
    )


_COMPARISON_COLUMNS = (
    "Kontekst",
    "Grupa EMS",
    "Liczba",
    "Średnia (dni)",
    "Mediana (dni)",
    "Min (dni)",
    "Max (dni)",
    "P25 (dni)",
    "P75 (dni)",
)

_ULCER_COMPARISON_COLUMNS = (
    "Typ wrzodu",
    "Grupa EMS",
    "Liczba",
    "Średnia (dni)",
    "Mediana (dni)",
    "Min (dni)",
    "Max (dni)",
    "P25 (dni)",
    "P75 (dni)",
)


def _comparison_table_rows(
    comparison: EmsComparisonRow | None,
) -> tuple[tuple[str, ...], ...]:
    if comparison is None:
        return ()
    rows: list[tuple[str, ...]] = []
    if comparison.ems_yes is not None:
        rows.append(
            (
                comparison.context_label,
                EMS_LABELS["yes"],
                *_duration_cells(comparison.ems_yes),
            )
        )
    if comparison.ems_no is not None:
        rows.append(
            (
                comparison.context_label,
                EMS_LABELS["no"],
                *_duration_cells(comparison.ems_no),
            )
        )
    return tuple(rows)


def _ulcer_comparison_table_rows(
    comparisons: tuple[EmsUlcerComparisonRow, ...],
) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    for comparison in comparisons:
        if comparison.ems_yes is not None:
            rows.append(
                (
                    comparison.ulcer_label,
                    EMS_LABELS["yes"],
                    *_duration_cells(comparison.ems_yes),
                )
            )
        if comparison.ems_no is not None:
            rows.append(
                (
                    comparison.ulcer_label,
                    EMS_LABELS["no"],
                    *_duration_cells(comparison.ems_no),
                )
            )
    return tuple(rows)


def _breed_comparison_table_rows(
    comparisons: tuple[EmsBreedComparisonRow, ...],
) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    for comparison in comparisons:
        if comparison.ems_yes is not None:
            rows.append(
                (
                    comparison.breed_label,
                    EMS_LABELS["yes"],
                    *_duration_cells(comparison.ems_yes),
                )
            )
        if comparison.ems_no is not None:
            rows.append(
                (
                    comparison.breed_label,
                    EMS_LABELS["no"],
                    *_duration_cells(comparison.ems_no),
                )
            )
    return tuple(rows)


def build_summary_details(result: EmsTreatmentDurationResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przeanalizować czasu leczenia."

    exclusions = result.exclusions
    surgery = result.surgery_rate
    surgery_total = (
        surgery.overall_summary.total_cases
        if surgery.overall_summary is not None
        else surgery.exclusions.included_broader_cases
    )
    return (
        f"Źródła danych: {result.source_clinical_label}, {result.source_patient_label}. "
        f"Blok EMS: wyłącznie uleczone przypadki wrzodowe leczone farmakologicznie "
        f"(farmacology_surgery = f) z prawidłowym EMS (tak/nie) na wierszu kończącym "
        f"leczenie — uwzględniono {exclusions.included_pharmacological_ems_cases} przypadków "
        f"({exclusions.included_ems_yes} z EMS, {exclusions.included_ems_no} bez EMS). "
        f"Blok zabiegu: szersza kohorta zamkniętych przypadków wrzodowych z "
        f"farmacology_surgery = f lub s — uwzględniono {surgery_total} przypadków."
    )


def build_interpretation_summary(result: EmsTreatmentDurationResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przygotować interpretacji."

    exclusions = result.exclusions
    if exclusions.included_pharmacological_ems_cases == 0:
        return (
            "Brak uleczonych przypadków wrzodowych leczonych farmakologicznie "
            "z prawidłowym EMS i obliczalnym czasem leczenia."
        )

    parts = [
        (
            "Wyniki opisują wyłącznie skojarzenie — nie dowodzą przyczynowego "
            "wpływu EMS na czas leczenia."
        ),
        (
            "Zakres obejmuje tylko rzeczywiste wrzody (z wyłączeniem typów x i xxx), "
            "uleczone (how_ended = good), z farmakologią (farmacology_surgery = f) "
            "oraz EMS = tak/nie odczytanym z wiersza kończącego leczenie."
        ),
        (
            f"Do analizy włączono {exclusions.included_pharmacological_ems_cases} "
            f"przypadków: {exclusions.included_ems_yes} z EMS i "
            f"{exclusions.included_ems_no} bez EMS."
        ),
    ]

    overall_test = next(
        (
            test
            for test in result.statistical_tests
            if test.comparison_label == "Łącznie — EMS tak vs EMS nie"
        ),
        None,
    )
    if overall_test and not overall_test.note:
        parts.append(
            f"Łącznie mediana różnicy wynosi {overall_test.median_difference_days} dni "
            f"(EMS tak − EMS nie); kierunek: {overall_test.direction}; "
            f"p={overall_test.raw_p_value}."
        )
    elif overall_test:
        parts.append(f"Łącznie: {overall_test.note}.")

    if result.ulcer_comparisons:
        clearest = None
        for test in result.statistical_tests:
            if "Łącznie —" not in test.comparison_label or ":" not in test.comparison_label:
                continue
            if test.note:
                continue
            if clearest is None:
                clearest = test
        if clearest:
            parts.append(
                f"Najwyraźniejszy sygnał w podziale według typu wrzodu: "
                f"{clearest.comparison_label} (p={clearest.raw_p_value}, "
                f"różnica mediany {clearest.median_difference_days} dni, "
                f"{clearest.direction})."
            )

    sparse_ulcers = [
        comparison.ulcer_label
        for comparison in result.ulcer_comparisons
        if comparison.ems_yes is None or comparison.ems_no is None
    ]
    if sparse_ulcers:
        joined = ", ".join(sparse_ulcers[:5])
        parts.append(
            f"Dla typów wrzodu: {joined} brakuje wystarczającej liczby przypadków "
            f"w co najmniej jednej grupie EMS (n<{MIN_DISPLAY_GROUP_SIZE}) — "
            f"wnioski są ograniczone."
        )

    if exclusions.excluded_unknown_species > 0:
        parts.append(
            f"{exclusions.excluded_unknown_species} przypadków pominięto w analizach "
            f"gatunkowych z powodu nieznanego gatunku, ale mogą być uwzględnione "
            f"w porównaniu łącznym."
        )

    if result.dog_breed_comparisons:
        parts.append(
            f"Warstwa rasowa (psy) obejmuje {len(result.dog_breed_comparisons)} ras "
            f"z co najmniej jedną grupą EMS o n≥{MIN_DISPLAY_GROUP_SIZE}."
        )
    else:
        parts.append(
            "Warstwa rasowa (psy) nie została pokazana — zbyt mała liczba przypadków "
            f"w grupach EMS (n<{MIN_DISPLAY_GROUP_SIZE})."
        )

    return " ".join(parts)


def build_descriptive_stats_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    exclusions = result.exclusions
    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba wierszy clinical (N)", str(exclusions.total_clinical_rows)),
            ("Wykluczone — nie wrzód (n)", str(exclusions.excluded_non_ulcer)),
            ("Wykluczone — inne zakończenie niż good (n)", str(exclusions.excluded_not_good)),
            ("Wykluczone — enukleacja (n)", str(exclusions.excluded_enucleation)),
            ("Wykluczone — brak kontroli (n)", str(exclusions.excluded_no_followup)),
            ("Wykluczone — kontynuacja leczenia (n)", str(exclusions.excluded_continuation)),
            (
                "Wykluczone — brak obliczalnego czasu leczenia (n)",
                str(exclusions.excluded_duration_unavailable),
            ),
            (
                "Uwzględnione — uleczone z czasem leczenia (n)",
                str(exclusions.included_healed_with_duration),
            ),
            (
                "Wykluczone — nie farmakologiczne (n)",
                str(exclusions.excluded_non_pharmacological),
            ),
            ("Wykluczone — nieprawidłowy EMS (n)", str(exclusions.excluded_invalid_ems)),
            ("Wykluczone — nieprawidłowy typ wrzodu (n)", str(exclusions.excluded_invalid_ulcer)),
            (
                "Pominięte w analizach gatunkowych — nieznany gatunek (n)",
                str(exclusions.excluded_unknown_species),
            ),
            ("Wykluczone — nieznana rasa (psy) (n)", str(exclusions.excluded_unknown_breed)),
            (
                "Uwzględnione — farmakologia + EMS (n)",
                str(exclusions.included_pharmacological_ems_cases),
            ),
            ("Uwzględnione — EMS tak (n)", str(exclusions.included_ems_yes)),
            ("Uwzględnione — EMS nie (n)", str(exclusions.included_ems_no)),
        ),
    )


def exclusions_table_block(result: EmsTreatmentDurationResult) -> ReportTableBlock:
    exclusions = result.exclusions
    return ReportTableBlock(
        title="Podsumowanie wykluczeń",
        columns=("Kategoria wykluczenia", "Liczba"),
        rows=(
            ("Nie wrzód", str(exclusions.excluded_non_ulcer)),
            ("Inne zakończenie niż good", str(exclusions.excluded_not_good)),
            ("Enukleacja", str(exclusions.excluded_enucleation)),
            ("Brak kontroli", str(exclusions.excluded_no_followup)),
            ("Kontynuacja leczenia", str(exclusions.excluded_continuation)),
            ("Brak obliczalnego czasu leczenia", str(exclusions.excluded_duration_unavailable)),
            ("Nie farmakologiczne (farmacology_surgery ≠ f)", str(exclusions.excluded_non_pharmacological)),
            ("Nieprawidłowy lub brakujący EMS", str(exclusions.excluded_invalid_ems)),
            ("Nieprawidłowy typ wrzodu", str(exclusions.excluded_invalid_ulcer)),
            (
                "Pominięte w analizach gatunkowych — nieznany gatunek",
                str(exclusions.excluded_unknown_species),
            ),
            ("Nieznana rasa (psy)", str(exclusions.excluded_unknown_breed)),
        ),
    )


def overall_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia — EMS tak vs EMS nie (łącznie: psy i koty)",
        columns=_COMPARISON_COLUMNS,
        rows=_comparison_table_rows(result.overall_comparison),
    )


def ulcer_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Czas leczenia — EMS tak vs EMS nie według typu wrzodu (łącznie; "
            f"grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=_ULCER_COMPARISON_COLUMNS,
        rows=_ulcer_comparison_table_rows(result.ulcer_comparisons),
    )


def dog_overall_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia — EMS tak vs EMS nie (psy)",
        columns=_COMPARISON_COLUMNS,
        rows=_comparison_table_rows(result.dog_overall_comparison),
    )


def cat_overall_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia — EMS tak vs EMS nie (koty)",
        columns=_COMPARISON_COLUMNS,
        rows=_comparison_table_rows(result.cat_overall_comparison),
    )


def dog_ulcer_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Czas leczenia — EMS tak vs EMS nie według typu wrzodu (psy; "
            f"grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=_ULCER_COMPARISON_COLUMNS,
        rows=_ulcer_comparison_table_rows(result.dog_ulcer_comparisons),
    )


def cat_ulcer_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Czas leczenia — EMS tak vs EMS nie według typu wrzodu (koty; "
            f"grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=_ULCER_COMPARISON_COLUMNS,
        rows=_ulcer_comparison_table_rows(result.cat_ulcer_comparisons),
    )


def dog_breed_comparison_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Czas leczenia — EMS tak vs EMS nie według rasy (psy; "
            f"grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=("Rasa", *_ULCER_COMPARISON_COLUMNS[1:]),
        rows=_breed_comparison_table_rows(result.dog_breed_comparisons),
    )


def statistical_tests_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Porównania statystyczne (Mann–Whitney U)",
        columns=(
            "Porównanie",
            "Test",
            "p-value",
            "p-value (BH)",
            "Różnica median (dni)",
            "Kierunek",
            "Uwagi",
        ),
        rows=tuple(
            (
                row.comparison_label,
                row.test_name,
                row.raw_p_value,
                row.corrected_p_value,
                row.median_difference_days,
                row.direction,
                row.note or "—",
            )
            for row in result.statistical_tests
        ),
    )


_SURGERY_SUMMARY_COLUMNS = (
    "Kontekst",
    "Liczba przypadków",
    "Tylko farmakologia (n)",
    "Tylko farmakologia (%)",
    "Farmakologia + zabieg (n)",
    "Farmakologia + zabieg (%)",
)

_SURGERY_ULCER_COLUMNS = (
    "Typ wrzodu",
    "Liczba przypadków",
    "Tylko farmakologia (n)",
    "Farmakologia + zabieg (n)",
    "Udział zabiegu (%)",
)


def _surgery_summary_table_rows(
    summaries: tuple[SurgeryRateSummaryRow, ...],
) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    for summary in summaries:
        rows.append(
            (
                summary.context_label,
                str(summary.total_cases),
                str(summary.pharmacology_only_count),
                _format_percent(summary.pharmacology_only_percent),
                str(summary.surgery_count),
                _format_percent(summary.surgery_percent),
            )
        )
    return tuple(rows)


def surgery_rate_exclusions_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    exclusions = result.surgery_rate.exclusions
    return ReportTableBlock(
        title="Wykluczenia — częstość zabiegu (szersza kohorta)",
        columns=("Kategoria", "Liczba"),
        rows=(
            ("Wiersze clinical — nie wrzód", str(exclusions.excluded_non_ulcer_rows)),
            (
                "Przypadki — nieprawidłowy typ wrzodu",
                str(exclusions.excluded_invalid_ulcer_cases),
            ),
            (
                "Przypadki — nieprawidłowe farmacology_surgery",
                str(exclusions.excluded_invalid_farmacology_cases),
            ),
            (
                "Przypadki — nieznany gatunek (pominięte w warstwie gatunkowej)",
                str(exclusions.excluded_unknown_species_cases),
            ),
            (
                "Uwzględnione — zamknięte przypadki wrzodowe (f lub s)",
                str(exclusions.included_broader_cases),
            ),
        ),
    )


def surgery_rate_summary_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    summaries = tuple(
        summary
        for summary in (
            result.surgery_rate.overall_summary,
            result.surgery_rate.dog_summary,
            result.surgery_rate.cat_summary,
        )
        if summary is not None
    )
    return ReportTableBlock(
        title="Częstość konieczności zabiegu — podsumowanie (szersza kohorta wrzodowa)",
        columns=_SURGERY_SUMMARY_COLUMNS,
        rows=_surgery_summary_table_rows(summaries),
    )


def surgery_rate_ulcer_table_block(
    result: EmsTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Częstość konieczności zabiegu według typu wrzodu "
            f"(szersza kohorta; typy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=_SURGERY_ULCER_COLUMNS,
        rows=tuple(
            (
                row.ulcer_label,
                str(row.total_cases),
                str(row.pharmacology_only_count),
                str(row.surgery_count),
                _format_percent(row.surgery_percent),
            )
            for row in result.surgery_rate.ulcer_type_rows
        ),
    )


def build_surgery_rate_interpretation_summary(
    result: EmsTreatmentDurationResult,
) -> str:
    if not result.is_success:
        return ""

    block = result.surgery_rate
    overall = block.overall_summary
    if overall is None or overall.total_cases == 0:
        return (
            "W szerszej kohocie zamkniętych przypadków wrzodowych nie znaleziono "
            "przypadków z prawidłowym farmacology_surgery (f lub s) na wierszu "
            "kończącym leczenie."
        )

    parts = [
        (
            "Ten blok dotyczy szerszej kohorty zamkniętych przypadków wrzodowych "
            "(wszystkie zakończenia leczenia z prawidłowym farmacology_surgery = f lub s). "
            "Nie jest to ta sama kohorta co analiza czasu leczenia z EMS powyżej, która "
            "ogranicza się do uleczonych przypadków leczonych wyłącznie farmakologicznie."
        ),
        (
            f"W {overall.total_cases} przypadkach łącznie zabieg był stosowany w "
            f"{overall.surgery_count} ({_format_percent(overall.surgery_percent)}), "
            f"a wyłącznie farmakologia w {overall.pharmacology_only_count} "
            f"({_format_percent(overall.pharmacology_only_percent)})."
        ),
    ]

    if block.dog_summary is not None:
        dog = block.dog_summary
        parts.append(
            f"Psy (n={dog.total_cases}): zabieg w {dog.surgery_count} "
            f"({_format_percent(dog.surgery_percent)}), tylko farmakologia w "
            f"{dog.pharmacology_only_count} ({_format_percent(dog.pharmacology_only_percent)})."
        )
    if block.cat_summary is not None:
        cat = block.cat_summary
        parts.append(
            f"Koty (n={cat.total_cases}): zabieg w {cat.surgery_count} "
            f"({_format_percent(cat.surgery_percent)}), tylko farmakologia w "
            f"{cat.pharmacology_only_count} ({_format_percent(cat.pharmacology_only_percent)})."
        )

    if block.ulcer_type_rows:
        highest = max(block.ulcer_type_rows, key=lambda row: row.surgery_percent or 0.0)
        parts.append(
            f"Najwyższy udział zabiegu wśród typów wrzodu z n≥{MIN_DISPLAY_GROUP_SIZE}: "
            f"{highest.ulcer_label} ({_format_percent(highest.surgery_percent)})."
        )
    elif block.exclusions.included_broader_cases > 0:
        parts.append(
            f"Brak typów wrzodu z co najmniej {MIN_DISPLAY_GROUP_SIZE} przypadkami — "
            "podział według typu wrzodu nie został pokazany."
        )

    if block.exclusions.excluded_unknown_species_cases > 0:
        parts.append(
            f"{block.exclusions.excluded_unknown_species_cases} przypadków ma nieznany "
            "gatunek i jest pominiętych w warstwie gatunkowej, ale wliczonych do "
            "podsumowania łącznego."
        )

    return " ".join(parts)
