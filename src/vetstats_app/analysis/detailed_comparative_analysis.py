"""Statistical engine and result models for detailed comparative analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import mean, median, pstdev

import pandas as pd

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.services.app_event_logger import log_error
from vetstats_app.analysis.clinical_common import parse_clinical_dmy_date
from vetstats_app.analysis.detailed_comparative import (
    AGE_SOURCE_COLUMN,
    BLOCK_INSUFFICIENT_NUMERIC_SAMPLE,
    BLOCK_NO_AGE_DATA,
    BLOCK_NO_STATISTICAL_TEST,
    BLOCK_SCIPY_MISSING,
    BLOCK_STATISTICAL_TEST_EXECUTION_FAILED,
    AnalysisMode,
    AnalysisTarget,
    ComparativeGroupDefinition,
    CriterionMode,
    CriterionModeLabel,
    DetailedComparativeState,
    GroupCriterion,
    collect_target_values_for_patients,
    format_analysis_target_label,
    is_age_analysis_target,
    resolve_group_patient_ids,
    validate_detailed_comparative_state,
)
from vetstats_app.analysis.statistical_runtime import (
    format_statistical_runtime_error,
    scipy_missing_message,
)
from vetstats_app.analysis.patient_id_cross_table_summary import (
    TABLE_PATIENT_COLUMNS,
    normalize_patient_id,
)
from data_sterilizer.schemas.clinical import DATE_APPOINTMENT_COLUMN
from data_sterilizer.schemas.micro import DATE_COLLECT_COLUMN

ALPHA = 0.05
MIN_NUMERIC_GROUP_SIZE = 2
MIN_NORMALITY_SAMPLE = 3
MAX_NORMALITY_SAMPLE = 5000
MIN_CHI_SQUARE_EXPECTED = 5.0


@dataclass(frozen=True)
class CategoricalFrequencyRow:
    category: str
    group_1_count: int
    group_1_percent: float
    group_2_count: int
    group_2_percent: float


@dataclass(frozen=True)
class NumericDescriptiveRow:
    group_name: str
    n: int
    missing: int
    mean: float | None
    median: float | None
    std: float | None
    minimum: float | None
    maximum: float | None
    percentile_25: float | None
    percentile_75: float | None


@dataclass(frozen=True)
class StatisticalTestResult:
    test_name: str
    selection_rationale: str
    statistic: str
    p_value: str
    p_value_float: float | None
    is_significant: bool
    comparison_type: str
    normality_notes: str = ""


@dataclass(frozen=True)
class DetailedComparativeAnalysisResult:
    is_success: bool
    error_message: str | None = None
    variable_label: str = ""
    variable_table: str = ""
    variable_column: str = ""
    analysis_mode: AnalysisMode = AnalysisMode.CATEGORICAL
    group_1_name: str = ""
    group_2_name: str = ""
    group_1_patient_count: int = 0
    group_2_patient_count: int = 0
    group_1_with_data: int = 0
    group_2_with_data: int = 0
    group_1_missing: int = 0
    group_2_missing: int = 0
    overlap_patient_count: int = 0
    group_1_criteria_summary: tuple[str, ...] = ()
    group_2_criteria_summary: tuple[str, ...] = ()
    group_description_text: str = ""
    descriptive_summary_text: str = ""
    statistical_summary_text: str = ""
    interpretation_text: str = ""
    categorical_rows: tuple[CategoricalFrequencyRow, ...] = ()
    numeric_rows: tuple[NumericDescriptiveRow, ...] = ()
    test_result: StatisticalTestResult | None = None
    charts: tuple[AnalysisChartSpec, ...] = ()
    age_reference_date_note: str = ""
    warnings: tuple[str, ...] = ()


def format_criterion_line(criterion: GroupCriterion, index: int) -> str:
    mode_label = (
        CriterionModeLabel.MUST
        if criterion.mode == CriterionMode.MUST_CONTAIN
        else CriterionModeLabel.MAY
    )
    return (
        f"{index}. {criterion.table_name}.{criterion.column_name} "
        f"({mode_label}): {criterion.value}"
    )


def format_group_criteria_summary(group: ComparativeGroupDefinition) -> tuple[str, ...]:
    return tuple(
        format_criterion_line(criterion, index)
        for index, criterion in enumerate(group.complete_criteria, start=1)
    )


def format_detailed_analysis_settings_lines(
    state: DetailedComparativeState,
) -> tuple[str, ...]:
    mode_label = (
        "porównanie numeryczne"
        if state.analysis_target.mode == AnalysisMode.NUMERIC
        else "porównanie kategoryczne"
    )
    target_label = format_analysis_target_label(state.analysis_target)
    lines = [
        f"Zmienna: {target_label} ({mode_label})",
        f"{state.group_1.display_name}:",
    ]
    lines.extend(format_group_criteria_summary(state.group_1) or ("brak kryteriów",))
    lines.append(f"{state.group_2.display_name}:")
    lines.extend(format_group_criteria_summary(state.group_2) or ("brak kryteriów",))
    return tuple(lines)


def format_detailed_analysis_settings_summary(
    state: DetailedComparativeState,
) -> str:
    return " | ".join(format_detailed_analysis_settings_lines(state))


def run_detailed_comparative_analysis(
    datasets: dict[str, pd.DataFrame],
    state: DetailedComparativeState,
) -> DetailedComparativeAnalysisResult:
    validation = validate_detailed_comparative_state(datasets, state)
    if not validation.can_analyze:
        message = validation.blocking_messages[0] if validation.blocking_messages else (
            "Analiza nie może zostać uruchomiona."
        )
        return DetailedComparativeAnalysisResult(is_success=False, error_message=message)

    scipy_error = scipy_missing_message()
    if scipy_error is not None:
        log_error("detailed_analysis", "SciPy is not available in the runtime environment.")
        return DetailedComparativeAnalysisResult(is_success=False, error_message=scipy_error)

    group_1_ids = resolve_group_patient_ids(datasets, state.group_1)
    group_2_ids = resolve_group_patient_ids(datasets, state.group_2)
    target = state.analysis_target
    overlap = group_1_ids & group_2_ids

    base = DetailedComparativeAnalysisResult(
        is_success=True,
        variable_label=format_analysis_target_label(target),
        variable_table=target.table_name,
        variable_column=target.column_name,
        analysis_mode=target.mode,
        group_1_name=state.group_1.display_name,
        group_2_name=state.group_2.display_name,
        group_1_patient_count=len(group_1_ids),
        group_2_patient_count=len(group_2_ids),
        overlap_patient_count=len(overlap),
        group_1_criteria_summary=format_group_criteria_summary(state.group_1),
        group_2_criteria_summary=format_group_criteria_summary(state.group_2),
        warnings=validation.warning_messages,
    )

    if target.mode == AnalysisMode.CATEGORICAL:
        return _run_categorical_analysis(datasets, state, base, group_1_ids, group_2_ids)
    return _run_numeric_analysis(datasets, state, base, group_1_ids, group_2_ids)


def _run_categorical_analysis(
    datasets: dict[str, pd.DataFrame],
    state: DetailedComparativeState,
    base: DetailedComparativeAnalysisResult,
    group_1_ids: set[str],
    group_2_ids: set[str],
) -> DetailedComparativeAnalysisResult:
    target = state.analysis_target
    values_1 = collect_target_values_for_patients(datasets, target, group_1_ids)
    values_2 = collect_target_values_for_patients(datasets, target, group_2_ids)

    categories = sorted(set(values_1) | set(values_2), key=str.casefold)
    counts_1 = {category: values_1.count(category) for category in categories}
    counts_2 = {category: values_2.count(category) for category in categories}
    n1 = len(values_1)
    n2 = len(values_2)

    rows = tuple(
        CategoricalFrequencyRow(
            category=category,
            group_1_count=counts_1[category],
            group_1_percent=round((counts_1[category] / n1) * 100.0, 1) if n1 else 0.0,
            group_2_count=counts_2[category],
            group_2_percent=round((counts_2[category] / n2) * 100.0, 1) if n2 else 0.0,
        )
        for category in categories
    )

    test_result, test_error = _select_categorical_test(
        categories=categories,
        counts_1=[counts_1[category] for category in categories],
        counts_2=[counts_2[category] for category in categories],
        group_1_name=base.group_1_name,
        group_2_name=base.group_2_name,
    )
    if test_result is None:
        log_error(
            "detailed_analysis",
            (
                f"categorical test failed for {base.variable_label}; "
                f"n1={n1}, n2={n2}, categories={len(categories)}; detail={test_error}"
            ),
        )
        return DetailedComparativeAnalysisResult(
            is_success=False,
            error_message=_statistical_test_failure_message(
                samples_built=True,
                detail=test_error,
            ),
        )

    group_description = _build_group_description_text(base)
    descriptive_text = _build_categorical_descriptive_text(base, rows, n1, n2)
    statistical_text = _build_statistical_text(test_result)
    interpretation = _build_interpretation_text(
        base=base,
        test_result=test_result,
        extra=(
            f"Porównano rozkład kategorii zmiennej {base.variable_label} "
            f"między {base.group_1_name} (n={n1}) a {base.group_2_name} (n={n2})."
        ),
    )

    charts = (
        AnalysisChartSpec(
            chart_id="detailed_comparative_categorical_distribution",
            title="Rozkład kategorii w grupach",
            chart_type="stacked_bar",
            labels=tuple(row.category for row in rows),
            values=(),
            x_axis_label="Kategoria",
            y_axis_label="Liczba obserwacji",
            stacked_series_labels=(base.group_1_name, base.group_2_name),
            stacked_series_values=(
                tuple(float(row.group_1_count) for row in rows),
                tuple(float(row.group_2_count) for row in rows),
            ),
        ),
    )

    return DetailedComparativeAnalysisResult(
        is_success=True,
        variable_label=base.variable_label,
        variable_table=base.variable_table,
        variable_column=base.variable_column,
        analysis_mode=base.analysis_mode,
        group_1_name=base.group_1_name,
        group_2_name=base.group_2_name,
        group_1_patient_count=base.group_1_patient_count,
        group_2_patient_count=base.group_2_patient_count,
        group_1_with_data=n1,
        group_2_with_data=n2,
        group_1_missing=base.group_1_patient_count - n1,
        group_2_missing=base.group_2_patient_count - n2,
        overlap_patient_count=base.overlap_patient_count,
        group_1_criteria_summary=base.group_1_criteria_summary,
        group_2_criteria_summary=base.group_2_criteria_summary,
        group_description_text=group_description,
        descriptive_summary_text=descriptive_text,
        statistical_summary_text=statistical_text,
        interpretation_text=interpretation,
        categorical_rows=rows,
        test_result=test_result,
        charts=charts,
        warnings=base.warnings,
    )


def _run_numeric_analysis(
    datasets: dict[str, pd.DataFrame],
    state: DetailedComparativeState,
    base: DetailedComparativeAnalysisResult,
    group_1_ids: set[str],
    group_2_ids: set[str],
) -> DetailedComparativeAnalysisResult:
    target = state.analysis_target
    age_note = ""
    if is_age_analysis_target(target):
        numeric_1, note_1 = _collect_age_values(datasets, group_1_ids, state.group_1)
        numeric_2, note_2 = _collect_age_values(datasets, group_2_ids, state.group_2)
        age_note = _merge_age_notes(note_1, note_2)
    else:
        numeric_1 = _collect_numeric_values(datasets, target, group_1_ids)
        numeric_2 = _collect_numeric_values(datasets, target, group_2_ids)

    if len(numeric_1) < MIN_NUMERIC_GROUP_SIZE or len(numeric_2) < MIN_NUMERIC_GROUP_SIZE:
        return DetailedComparativeAnalysisResult(
            is_success=False,
            error_message=_numeric_sample_failure_message(
                numeric_1=numeric_1,
                numeric_2=numeric_2,
                is_age_target=is_age_analysis_target(target),
            ),
        )

    rows = (
        _numeric_descriptive_row(base.group_1_name, numeric_1, base.group_1_patient_count),
        _numeric_descriptive_row(base.group_2_name, numeric_2, base.group_2_patient_count),
    )

    test_result, test_error = _select_numeric_test(
        numeric_1=numeric_1,
        numeric_2=numeric_2,
        group_1_name=base.group_1_name,
        group_2_name=base.group_2_name,
    )
    if test_result is None:
        log_error(
            "detailed_analysis",
            (
                f"numeric test failed for {base.variable_label}; "
                f"n1={len(numeric_1)}, n2={len(numeric_2)}; detail={test_error}"
            ),
        )
        return DetailedComparativeAnalysisResult(
            is_success=False,
            error_message=_statistical_test_failure_message(
                samples_built=True,
                detail=test_error,
            ),
        )

    group_description = _build_group_description_text(base)
    if age_note:
        group_description += f"\n\n{age_note}"
    descriptive_text = _build_numeric_descriptive_text(rows)
    statistical_text = _build_statistical_text(test_result)
    interpretation = _build_interpretation_text(
        base=base,
        test_result=test_result,
        extra=(
            f"Porównano wartości numeryczne zmiennej {base.variable_label} "
            f"między {base.group_1_name} (n={len(numeric_1)}) "
            f"a {base.group_2_name} (n={len(numeric_2)}). "
            f"Próby traktowane jako niezależne."
        ),
    )

    charts = (
        AnalysisChartSpec(
            chart_id="detailed_comparative_numeric_boxplot",
            title="Rozkład wartości w grupach",
            chart_type="box",
            labels=(base.group_1_name, base.group_2_name),
            values=(),
            y_axis_label=base.variable_label,
            box_plot_groups=(tuple(numeric_1), tuple(numeric_2)),
        ),
    )

    return DetailedComparativeAnalysisResult(
        is_success=True,
        variable_label=base.variable_label,
        variable_table=base.variable_table,
        variable_column=base.variable_column,
        analysis_mode=base.analysis_mode,
        group_1_name=base.group_1_name,
        group_2_name=base.group_2_name,
        group_1_patient_count=base.group_1_patient_count,
        group_2_patient_count=base.group_2_patient_count,
        group_1_with_data=len(numeric_1),
        group_2_with_data=len(numeric_2),
        group_1_missing=base.group_1_patient_count - len(numeric_1),
        group_2_missing=base.group_2_patient_count - len(numeric_2),
        overlap_patient_count=base.overlap_patient_count,
        group_1_criteria_summary=base.group_1_criteria_summary,
        group_2_criteria_summary=base.group_2_criteria_summary,
        group_description_text=group_description,
        descriptive_summary_text=descriptive_text,
        statistical_summary_text=statistical_text,
        interpretation_text=interpretation,
        numeric_rows=rows,
        test_result=test_result,
        charts=charts,
        age_reference_date_note=age_note,
        warnings=base.warnings,
    )


def _collect_numeric_values(
    datasets: dict[str, pd.DataFrame],
    target: AnalysisTarget,
    patient_ids: set[str],
) -> tuple[float, ...]:
    values: list[float] = []
    for patient_id in sorted(patient_ids):
        raw_values = collect_target_values_for_patients(
            datasets,
            target,
            {patient_id},
        )
        for raw in raw_values:
            parsed = _parse_numeric_value(raw)
            if parsed is not None:
                values.append(parsed)
                break
    return tuple(values)


def _collect_age_values(
    datasets: dict[str, pd.DataFrame],
    patient_ids: set[str],
    group: ComparativeGroupDefinition,
) -> tuple[tuple[float, ...], str]:
    ages: list[float] = []
    reference_dates: list[date] = []
    for patient_id in sorted(patient_ids):
        birth_date = _patient_date_of_birth(datasets, patient_id)
        reference_date = _reference_date_for_group_member(
            datasets,
            patient_id,
            group,
        )
        if birth_date is None or reference_date is None:
            continue
        reference_dates.append(reference_date)
        age_years = (reference_date - birth_date).days / 365.25
        ages.append(age_years)

    return tuple(ages), _build_age_reference_note(group, reference_dates)


def _build_age_reference_note(
    group: ComparativeGroupDefinition,
    reference_dates: list[date],
) -> str:
    unit_note = _age_unit_note_for_group(group)
    if not reference_dates:
        return (
            f"{unit_note} Wiek obliczono z patient.date_of_birth, lecz brak daty "
            "odniesienia w rekordach pasujących do kryteriów grupy."
        )

    unique_dates = sorted({value.isoformat() for value in reference_dates})
    if len(unique_dates) == 1:
        date_note = (
            "Data odniesienia pochodzi z rekordów spełniających kryteria grupy: "
            f"{unique_dates[0]}."
        )
    else:
        date_note = (
            "Daty odniesienia pochodzą z rekordów spełniających kryteria grupy "
            f"(zakres: {unique_dates[0]} – {unique_dates[-1]})."
        )
    return f"{unit_note} {date_note}"


def _age_unit_note_for_group(group: ComparativeGroupDefinition) -> str:
    if _group_has_table_criteria(group, "clinical"):
        return (
            "Jednostka analizy wieku: jeden pacjent na obserwację; data odniesienia "
            "pochodzi z rekordu clinical spełniającego kryteria grupy "
            "(najpóźniejsza pasująca wizyta pacjenta)."
        )
    if _group_has_table_criteria(group, "micro"):
        return (
            "Jednostka analizy wieku: jeden pacjent na obserwację; data odniesienia "
            "pochodzi z rekordu micro spełniającego kryteria grupy "
            "(najpóźniejsze pasujące pobranie pacjenta)."
        )
    return (
        "Jednostka analizy wieku: jeden pacjent na obserwację; data odniesienia "
        "pochodzi z najpóźniejszej wizyty clinical lub pobrania micro pacjenta."
    )


def _group_has_table_criteria(group: ComparativeGroupDefinition, table_name: str) -> bool:
    return any(
        criterion.table_name == table_name and criterion.mode == CriterionMode.MUST_CONTAIN
        for criterion in group.complete_criteria
    )


def _merge_age_notes(note_1: str, note_2: str) -> str:
    if note_1 == note_2:
        return note_1
    if not note_1:
        return note_2
    if not note_2:
        return note_1
    return f"{note_1}\n\n{note_2}"


def _statistical_test_failure_message(*, samples_built: bool, detail: str | None) -> str:
    if samples_built and detail:
        runtime_detail = format_statistical_runtime_error(detail)
        if runtime_detail == BLOCK_SCIPY_MISSING:
            return BLOCK_SCIPY_MISSING
        return BLOCK_STATISTICAL_TEST_EXECUTION_FAILED.format(detail=runtime_detail)
    if samples_built:
        return BLOCK_NO_STATISTICAL_TEST
    return BLOCK_NO_STATISTICAL_TEST


def _numeric_sample_failure_message(
    *,
    numeric_1: tuple[float, ...],
    numeric_2: tuple[float, ...],
    is_age_target: bool,
) -> str:
    if is_age_target and (not numeric_1 or not numeric_2):
        return BLOCK_NO_AGE_DATA
    if len(numeric_1) < MIN_NUMERIC_GROUP_SIZE or len(numeric_2) < MIN_NUMERIC_GROUP_SIZE:
        return BLOCK_INSUFFICIENT_NUMERIC_SAMPLE
    return BLOCK_NO_STATISTICAL_TEST


def _reference_date_for_group_member(
    datasets: dict[str, pd.DataFrame],
    patient_id: str,
    group: ComparativeGroupDefinition,
) -> date | None:
    clinical_criteria = _must_criteria_for_table(group, "clinical")
    if clinical_criteria:
        clinical_dates = _dates_from_matching_rows(
            datasets,
            table_name="clinical",
            patient_id=patient_id,
            criteria=clinical_criteria,
            date_column_name=DATE_APPOINTMENT_COLUMN,
        )
        if clinical_dates:
            return max(clinical_dates)

    micro_criteria = _must_criteria_for_table(group, "micro")
    if micro_criteria:
        micro_dates = _dates_from_matching_rows(
            datasets,
            table_name="micro",
            patient_id=patient_id,
            criteria=micro_criteria,
            date_column_name=DATE_COLLECT_COLUMN,
        )
        if micro_dates:
            return max(micro_dates)

    clinical_date = _latest_date_for_patient(
        datasets.get("clinical"),
        patient_id,
        DATE_APPOINTMENT_COLUMN,
        table_name="clinical",
    )
    if clinical_date is not None:
        return clinical_date
    return _latest_date_for_patient(
        datasets.get("micro"),
        patient_id,
        DATE_COLLECT_COLUMN,
        table_name="micro",
    )


def _must_criteria_for_table(
    group: ComparativeGroupDefinition,
    table_name: str,
) -> tuple[GroupCriterion, ...]:
    return tuple(
        criterion
        for criterion in group.complete_criteria
        if criterion.table_name == table_name
        and criterion.mode == CriterionMode.MUST_CONTAIN
    )


def _dates_from_matching_rows(
    datasets: dict[str, pd.DataFrame],
    *,
    table_name: str,
    patient_id: str,
    criteria: tuple[GroupCriterion, ...],
    date_column_name: str,
) -> list[date]:
    frame = datasets.get(table_name)
    if frame is None or not criteria:
        return []

    patient_column = _resolve_column(frame, TABLE_PATIENT_COLUMNS[table_name])
    date_column = _resolve_column(frame, date_column_name)
    if patient_column is None or date_column is None:
        return []

    dates: list[date] = []
    for _, row in frame.iterrows():
        if normalize_patient_id(row[patient_column]) != patient_id:
            continue
        if not _row_matches_criteria(row, frame, criteria):
            continue
        parsed = parse_clinical_dmy_date(row[date_column])
        if parsed is not None:
            dates.append(parsed)
    return dates


def _row_matches_criteria(
    row: pd.Series,
    frame: pd.DataFrame,
    criteria: tuple[GroupCriterion, ...],
) -> bool:
    for criterion in criteria:
        value_column = _resolve_column(frame, criterion.column_name)
        if value_column is None:
            return False
        cell_value = _normalize_cell_value(row[value_column])
        if cell_value is None or cell_value.casefold() != criterion.value.strip().casefold():
            return False
    return True


def _normalize_cell_value(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "xxx":
        return None
    return text


def _patient_date_of_birth(
    datasets: dict[str, pd.DataFrame],
    patient_id: str,
) -> date | None:
    frame = datasets.get("patient")
    if frame is None:
        return None
    patient_column = _resolve_column(frame, TABLE_PATIENT_COLUMNS["patient"])
    dob_column = _resolve_column(frame, AGE_SOURCE_COLUMN)
    if patient_column is None or dob_column is None:
        return None
    for _, row in frame.iterrows():
        if normalize_patient_id(row[patient_column]) != patient_id:
            continue
        return parse_clinical_dmy_date(row[dob_column])
    return None


def _latest_date_for_patient(
    frame: pd.DataFrame | None,
    patient_id: str,
    date_column_name: str,
    *,
    table_name: str,
) -> date | None:
    if frame is None:
        return None
    patient_column = _resolve_column(frame, TABLE_PATIENT_COLUMNS[table_name])
    date_column = _resolve_column(frame, date_column_name)
    if patient_column is None or date_column is None:
        return None

    latest: date | None = None
    for _, row in frame.iterrows():
        if normalize_patient_id(row[patient_column]) != patient_id:
            continue
        parsed = parse_clinical_dmy_date(row[date_column])
        if parsed is None:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _resolve_column(frame: pd.DataFrame, column_name: str) -> str | None:
    if column_name in frame.columns:
        return column_name
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    return lower_to_actual.get(column_name.lower())


def _parse_numeric_value(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _numeric_descriptive_row(
    group_name: str,
    values: tuple[float, ...],
    total_patients: int,
) -> NumericDescriptiveRow:
    if not values:
        return NumericDescriptiveRow(
            group_name=group_name,
            n=0,
            missing=total_patients,
            mean=None,
            median=None,
            std=None,
            minimum=None,
            maximum=None,
            percentile_25=None,
            percentile_75=None,
        )

    sorted_values = sorted(values)
    q25 = _percentile(sorted_values, 25)
    q75 = _percentile(sorted_values, 75)
    std = pstdev(values) if len(values) > 1 else 0.0
    return NumericDescriptiveRow(
        group_name=group_name,
        n=len(values),
        missing=max(total_patients - len(values), 0),
        mean=round(mean(values), 2),
        median=round(median(values), 2),
        std=round(std, 2),
        minimum=round(sorted_values[0], 2),
        maximum=round(sorted_values[-1], 2),
        percentile_25=round(q25, 2) if q25 is not None else None,
        percentile_75=round(q75, 2) if q75 is not None else None,
    )


def _percentile(sorted_values: list[float], percentile: int) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (percentile / 100) * (len(sorted_values) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[lower]
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _is_normal_sample(values: tuple[float, ...]) -> tuple[bool, str]:
    if len(values) < MIN_NORMALITY_SAMPLE:
        return False, f"n={len(values)} (< {MIN_NORMALITY_SAMPLE})"
    if len(values) > MAX_NORMALITY_SAMPLE:
        return False, f"n={len(values)} (> {MAX_NORMALITY_SAMPLE})"
    try:
        from scipy.stats import shapiro

        _, p_value = shapiro(values)
        if p_value >= ALPHA:
            return True, f"Shapiro–Wilk p={p_value:.4f}"
        return False, f"Shapiro–Wilk p={p_value:.4f}"
    except Exception:
        return False, "test Shapiro–Wilk niedostępny"


def _select_numeric_test(
    *,
    numeric_1: tuple[float, ...],
    numeric_2: tuple[float, ...],
    group_1_name: str,
    group_2_name: str,
) -> tuple[StatisticalTestResult | None, str | None]:
    normal_1, note_1 = _is_normal_sample(numeric_1)
    normal_2, note_2 = _is_normal_sample(numeric_2)
    normality_notes = f"{group_1_name}: {note_1}; {group_2_name}: {note_2}"
    last_error: str | None = None

    if normal_1 and normal_2:
        try:
            from scipy.stats import ttest_ind

            statistic, p_value = ttest_ind(numeric_1, numeric_2, equal_var=False)
            return StatisticalTestResult(
                test_name="test t Studenta (Welcha)",
                selection_rationale=(
                    "Obie grupy spełniły wstępne założenie normalności (Shapiro–Wilk, α=0,05), "
                    "dlatego zastosowano dwuwymiarowy test t dla prób niezależnych z wariancją nierówną."
                ),
                statistic=f"{statistic:.4f}",
                p_value=f"{p_value:.4f}",
                p_value_float=p_value,
                is_significant=p_value < ALPHA,
                comparison_type="niezależne",
                normality_notes=normality_notes,
            ), None
        except Exception as exc:
            last_error = str(exc)

    try:
        from scipy.stats import mannwhitneyu

        statistic, p_value = mannwhitneyu(
            numeric_1,
            numeric_2,
            alternative="two-sided",
        )
        return StatisticalTestResult(
            test_name="Mann–Whitney U",
            selection_rationale=(
                "Przynajmniej jedna grupa nie spełniła założenia normalności lub próba była "
                "zbyt mała dla Shapiro–Wilka, dlatego zastosowano nieparametryczny test "
                "Mann–Whitney U dla prób niezależnych."
            ),
            statistic=f"{statistic:.4f}",
            p_value=f"{p_value:.4f}",
            p_value_float=p_value,
            is_significant=p_value < ALPHA,
            comparison_type="niezależne",
            normality_notes=normality_notes,
        ), None
    except Exception as exc:
        return None, last_error or str(exc)


def _select_categorical_test(
    *,
    categories: list[str],
    counts_1: list[int],
    counts_2: list[int],
    group_1_name: str,
    group_2_name: str,
) -> tuple[StatisticalTestResult | None, str | None]:
    if len(categories) < 2:
        return None, "mniej niż dwie kategorie w zbudowanych próbkach"

    table = [counts_1, counts_2]
    if sum(counts_1) == 0 or sum(counts_2) == 0:
        return None, "pusta próba w jednej z grup"

    last_error: str | None = None
    if len(categories) == 2 and _should_use_fisher_exact(table):
        try:
            from scipy.stats import fisher_exact

            odds_ratio, p_value = fisher_exact(table)
            return StatisticalTestResult(
                test_name="dokładny test Fishera",
                selection_rationale=(
                    "Tabela kontyngencji 2×2 z małą oczekiwaną liczebnością komórek — "
                    "zastosowano dokładny test Fishera zamiast chi-kwadrat."
                ),
                statistic=f"OR={odds_ratio:.4f}",
                p_value=f"{p_value:.4f}",
                p_value_float=p_value,
                is_significant=p_value < ALPHA,
                comparison_type="niezależne",
            ), None
        except Exception as exc:
            last_error = str(exc)

    try:
        from scipy.stats import chi2_contingency

        chi2, p_value, _dof, expected = chi2_contingency(table)
        expected_note = (
            "oczekiwane liczebności ≥ 5"
            if _expected_counts_ok(expected)
            else "niespełnione założenie o oczekiwanych liczebnościach"
        )
        return StatisticalTestResult(
            test_name="chi-kwadrat Pearsona",
            selection_rationale=(
                f"Porównano rozkład kategorii między {group_1_name} i {group_2_name} "
                f"testem chi-kwadrat niezależności ({expected_note})."
            ),
            statistic=f"{chi2:.4f}",
            p_value=f"{p_value:.4f}",
            p_value_float=p_value,
            is_significant=p_value < ALPHA,
            comparison_type="niezależne",
        ), None
    except Exception as exc:
        return None, last_error or str(exc)


def _should_use_fisher_exact(table: list[list[int]]) -> bool:
    try:
        from scipy.stats import chi2_contingency

        _chi2, _p, _dof, expected = chi2_contingency(table)
        return not _expected_counts_ok(expected)
    except Exception:
        return True


def _expected_counts_ok(expected) -> bool:
    return all(float(value) >= MIN_CHI_SQUARE_EXPECTED for value in expected.flatten())


def _build_group_description_text(base: DetailedComparativeAnalysisResult) -> str:
    lines = [
        f"Zmienna analizy: {base.variable_label} "
        f"({ 'kategoryczna' if base.analysis_mode == AnalysisMode.CATEGORICAL else 'numeryczna' }).",
        f"{base.group_1_name}: n = {base.group_1_patient_count} pacjentów.",
        f"{base.group_2_name}: n = {base.group_2_patient_count} pacjentów.",
    ]
    if base.overlap_patient_count:
        lines.append(
            f"Pacjenci wspólni dla obu grup: {base.overlap_patient_count} "
            "(próby traktowane jako niezależne w teście)."
        )
    lines.append("")
    lines.append(f"Kryteria {base.group_1_name}:")
    lines.extend(base.group_1_criteria_summary or ("brak",))
    lines.append("")
    lines.append(f"Kryteria {base.group_2_name}:")
    lines.extend(base.group_2_criteria_summary or ("brak",))
    return "\n".join(lines)


def _build_categorical_descriptive_text(
    base: DetailedComparativeAnalysisResult,
    rows: tuple[CategoricalFrequencyRow, ...],
    n1: int,
    n2: int,
) -> str:
    lines = [
        f"{base.group_1_name}: {n1} obserwacji, brakujące = {base.group_1_patient_count - n1}.",
        f"{base.group_2_name}: {n2} obserwacji, brakujące = {base.group_2_patient_count - n2}.",
        "",
        "Rozkład kategorii:",
    ]
    for row in rows:
        lines.append(
            f"- {row.category}: {base.group_1_name} {row.group_1_count} ({row.group_1_percent}%), "
            f"{base.group_2_name} {row.group_2_count} ({row.group_2_percent}%)"
        )
    return "\n".join(lines)


def _build_numeric_descriptive_text(rows: tuple[NumericDescriptiveRow, ...]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.append(
            f"{row.group_name}: n = {row.n}, brakujące = {row.missing}, "
            f"średnia = {_format_optional(row.mean)}, mediana = {_format_optional(row.median)}, "
            f"SD = {_format_optional(row.std)}, min = {_format_optional(row.minimum)}, "
            f"max = {_format_optional(row.maximum)}, Q1 = {_format_optional(row.percentile_25)}, "
            f"Q3 = {_format_optional(row.percentile_75)}"
        )
    return "\n".join(lines)


def _build_statistical_text(test_result: StatisticalTestResult) -> str:
    significance = (
        "istotne statystycznie (p < 0,05)"
        if test_result.is_significant
        else "nieistotne statystycznie (p ≥ 0,05)"
    )
    lines = [
        f"Test: {test_result.test_name}",
        f"Typ porównania: {test_result.comparison_type}",
        f"Uzasadnienie wyboru: {test_result.selection_rationale}",
    ]
    if test_result.normality_notes:
        lines.append(f"Normalność: {test_result.normality_notes}")
    lines.extend(
        [
            f"Statystyka testowa: {test_result.statistic}",
            f"p = {test_result.p_value}",
            f"Wynik: {significance}",
        ]
    )
    return "\n".join(lines)


def _build_interpretation_text(
    *,
    base: DetailedComparativeAnalysisResult,
    test_result: StatisticalTestResult,
    extra: str,
) -> str:
    if test_result.is_significant:
        conclusion = (
            f"Wykryto statystycznie istotną różnicę w zmiennej {base.variable_label} "
            f"między {base.group_1_name} a {base.group_2_name}."
        )
    else:
        conclusion = (
            f"Nie wykazano statystycznie istotnej różnicy w zmiennej {base.variable_label} "
            f"między {base.group_1_name} a {base.group_2_name}."
        )
    lines = [extra, conclusion, f"Zastosowany test: {test_result.test_name}."]
    if base.warnings:
        lines.append("")
        lines.append("Ostrzeżenia:")
        lines.extend(f"- {warning}" for warning in base.warnings)
    return "\n".join(lines)


def _format_optional(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"
