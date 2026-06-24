"""Models and logic for detailed comparative group analysis (step 1: grouping + validation)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

import pandas as pd

from vetstats_app.analysis.patient_id_cross_table_summary import (
    TABLE_PATIENT_COLUMNS,
    normalize_patient_id,
)
from vetstats_app.services.preview_data_service import TABLE_FILE_NAMES

MAX_CRITERIA_PER_GROUP = 10
DEFAULT_GROUP_1_NAME = "Grupa 1"
DEFAULT_GROUP_2_NAME = "Grupa 2"
UNKNOWN_VALUE = "xxx"

BLOCK_NO_GROUP_1_CRITERIA = "Dodaj co najmniej jedno kryterium do Grupy 1."
BLOCK_NO_GROUP_2_CRITERIA = "Dodaj co najmniej jedno kryterium do Grupy 2."
BLOCK_NO_ANALYSIS_TARGET = "Wybierz, co chcesz analizować i porównywać między grupami."
BLOCK_ZERO_GROUP_SIZE = (
    "Nie można uruchomić analizy: jedna z grup ma liczebność n = 0."
)
BLOCK_IDENTICAL_GROUPS = (
    "Nie można uruchomić analizy: obie grupy są tożsame i nie mogą zostać porównane."
)
BLOCK_NO_VARIABLE_DATA = (
    "Nie można wykonać analizy: brak danych dla wybranej zmiennej w jednej lub obu grupach."
)
BLOCK_VARIABLE_MODE_MISMATCH = (
    "Wybrana zmienna nie może zostać porównana w tym trybie analizy."
)
BLOCK_NO_STATISTICAL_TEST = (
    "Nie można dobrać odpowiedniego testu statystycznego dla wybranego porównania."
)
BLOCK_NO_AGE_DATA = (
    "Nie można obliczyć wieku: brak patient.date_of_birth lub daty odniesienia "
    "dla pacjentów w jednej lub obu grupach."
)
BLOCK_INSUFFICIENT_NUMERIC_SAMPLE = (
    "Każda grupa musi mieć co najmniej dwie obserwacje numeryczne do porównania."
)
BLOCK_STATISTICAL_TEST_EXECUTION_FAILED = (
    "Nie udało się wykonać testu statystycznego dla zbudowanych próbek: {detail}"
)
BLOCK_SCIPY_MISSING = (
    "Nie można wykonać analizy statystycznej: brakuje wymaganej biblioteki SciPy."
)

WARNING_SMALL_GROUP = (
    "Mała liczebność jednej lub obu grup — wyniki mogą być niestabilne."
)
WARNING_IMBALANCED_GROUPS = (
    "Duża nierównowaga liczebności między grupami — interpretuj wyniki ostrożnie."
)
WARNING_MANY_MISSING_VALUES = (
    "Wiele brakujących wartości dla wybranej zmiennej — wyniki mogą być niepewne."
)

TABLE_DISPLAY_LABELS: dict[str, str] = {
    "patient": "patient",
    "clinical": "clinical",
    "micro": "micro",
}


class CriterionMode(str, Enum):
    MAY_CONTAIN = "may_contain"
    MUST_CONTAIN = "must_contain"


class AnalysisMode(str, Enum):
    CATEGORICAL = "categorical"
    NUMERIC = "numeric"


class CriterionModeLabel:
    MAY = "może zawierać"
    MUST = "musi zawierać"


@dataclass(frozen=True)
class GroupCriterion:
    table_name: str
    column_name: str
    value: str
    mode: CriterionMode = CriterionMode.MUST_CONTAIN

    def is_complete(self) -> bool:
        return bool(
            self.table_name.strip()
            and self.column_name.strip()
            and self.value.strip()
        )


@dataclass(frozen=True)
class ComparativeGroupDefinition:
    default_name: str
    custom_name: str = ""
    criteria: tuple[GroupCriterion, ...] = ()

    @property
    def display_name(self) -> str:
        cleaned = self.custom_name.strip()
        return cleaned if cleaned else self.default_name

    @property
    def complete_criteria(self) -> tuple[GroupCriterion, ...]:
        return tuple(criterion for criterion in self.criteria if criterion.is_complete())


@dataclass(frozen=True)
class AnalysisTarget:
    table_name: str = ""
    column_name: str = ""
    mode: AnalysisMode = AnalysisMode.CATEGORICAL

    def is_complete(self) -> bool:
        return bool(self.table_name.strip() and self.column_name.strip())


@dataclass(frozen=True)
class GroupCountSummary:
    group_name: str
    patient_count: int
    share_percent: float | None


@dataclass(frozen=True)
class DetailedComparativeState:
    group_1: ComparativeGroupDefinition
    group_2: ComparativeGroupDefinition
    analysis_target: AnalysisTarget = AnalysisTarget()


@dataclass(frozen=True)
class DetailedComparativeValidation:
    blocking_messages: tuple[str, ...]
    warning_messages: tuple[str, ...]
    group_1_count: int
    group_2_count: int
    total_patient_count: int
    can_analyze: bool

    @property
    def status_message(self) -> str:
        if self.blocking_messages:
            return self.blocking_messages[0]
        if self.warning_messages:
            return self.warning_messages[0]
        if self.can_analyze:
            return "Analiza gotowa do uruchomienia."
        return ""


def default_detailed_comparative_state() -> DetailedComparativeState:
    return DetailedComparativeState(
        group_1=ComparativeGroupDefinition(default_name=DEFAULT_GROUP_1_NAME),
        group_2=ComparativeGroupDefinition(default_name=DEFAULT_GROUP_2_NAME),
    )


def mirror_group_2_structure(
    group_1: ComparativeGroupDefinition,
    group_2: ComparativeGroupDefinition,
) -> ComparativeGroupDefinition:
    """Keep Group 2 table/column aligned with Group 1; preserve values where possible."""
    mirrored: list[GroupCriterion] = []
    for index, criterion_1 in enumerate(group_1.criteria):
        existing = group_2.criteria[index] if index < len(group_2.criteria) else None
        preserved_value = ""
        if (
            existing is not None
            and existing.table_name == criterion_1.table_name
            and existing.column_name == criterion_1.column_name
        ):
            preserved_value = existing.value
        mirrored.append(
            GroupCriterion(
                table_name=criterion_1.table_name,
                column_name=criterion_1.column_name,
                value=preserved_value,
                mode=criterion_1.mode,
            )
        )
    return replace(group_2, criteria=tuple(mirrored))


def _resolve_column(frame: pd.DataFrame, column_name: str) -> str | None:
    if column_name in frame.columns:
        return column_name
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    return lower_to_actual.get(column_name.lower())


def _normalize_cell_value(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == UNKNOWN_VALUE:
        return None
    return text


def list_table_names(datasets: dict[str, pd.DataFrame]) -> tuple[str, ...]:
    return tuple(name for name in TABLE_FILE_NAMES if name in datasets)


def list_columns_for_table(
    datasets: dict[str, pd.DataFrame],
    table_name: str,
) -> tuple[str, ...]:
    frame = datasets.get(table_name)
    if frame is None:
        return ()
    return tuple(str(column) for column in frame.columns)


# Synthetic analysis target for dynamically computed patient age.
COMPUTED_AGE_COLUMN = "__computed_patient_age__"
COMPUTED_AGE_DISPLAY_LABEL = "Wiek pacjenta (wyliczany dynamicznie)"
EXCLUDED_ANALYSIS_TARGET_COLUMNS = frozenset({"date_of_birth"})
# Age analysis uses patient.date_of_birth and a context-specific reference date.
AGE_SOURCE_COLUMN = "date_of_birth"
AGE_REFERENCE_NOTE = (
    "Wiek zostanie obliczony dynamicznie na podstawie patient.date_of_birth "
    "oraz daty odniesienia zależnej od kontekstu danych."
)


def list_analysis_target_columns(
    datasets: dict[str, pd.DataFrame],
    table_name: str,
) -> tuple[tuple[str, str], ...]:
    """Return (column_id, display_label) pairs for the analysis-target selector."""
    options: list[tuple[str, str]] = []
    excluded = {column.casefold() for column in EXCLUDED_ANALYSIS_TARGET_COLUMNS}
    for column in list_columns_for_table(datasets, table_name):
        if column.casefold() in excluded:
            continue
        options.append((column, column))
    if table_name == "patient":
        options.append((COMPUTED_AGE_COLUMN, COMPUTED_AGE_DISPLAY_LABEL))
    return tuple(options)


def format_analysis_target_label(target: AnalysisTarget) -> str:
    if is_age_analysis_target(target):
        return f"{target.table_name}.{COMPUTED_AGE_DISPLAY_LABEL}"
    return f"{target.table_name}.{target.column_name}"


def coerce_analysis_mode(value: object | None) -> AnalysisMode:
    if isinstance(value, AnalysisMode):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        for mode in AnalysisMode:
            if mode.value == normalized:
                return mode
    return AnalysisMode.CATEGORICAL


def resolve_analysis_target_column(table_name: str, column_key: str) -> str:
    cleaned = column_key.strip()
    if not cleaned:
        return ""
    if table_name == "patient":
        if cleaned == COMPUTED_AGE_DISPLAY_LABEL:
            return COMPUTED_AGE_COLUMN
        if cleaned == COMPUTED_AGE_COLUMN:
            return COMPUTED_AGE_COLUMN
    return cleaned


def build_analysis_target(
    table_name: str,
    column_key: str,
    mode_value: object | None,
) -> AnalysisTarget:
    table = table_name.strip()
    column = resolve_analysis_target_column(table, column_key)
    mode = coerce_analysis_mode(mode_value)
    if table == "patient" and column == COMPUTED_AGE_COLUMN:
        mode = AnalysisMode.NUMERIC
    return AnalysisTarget(table_name=table, column_name=column, mode=mode)


def list_distinct_column_values(
    datasets: dict[str, pd.DataFrame],
    table_name: str,
    column_name: str,
) -> tuple[str, ...]:
    frame = datasets.get(table_name)
    if frame is None:
        return ()
    column = _resolve_column(frame, column_name)
    if column is None:
        return ()

    values: list[str] = []
    seen: set[str] = set()
    for raw_value in frame[column].tolist():
        normalized = _normalize_cell_value(raw_value)
        if normalized is None:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(normalized)
    return tuple(sorted(values, key=str.casefold))


def all_valid_patient_ids(datasets: dict[str, pd.DataFrame]) -> set[str]:
    patient_frame = datasets.get("patient")
    if patient_frame is None:
        return set()
    column = _resolve_column(patient_frame, TABLE_PATIENT_COLUMNS["patient"])
    if column is None:
        return set()

    patient_ids: set[str] = set()
    for value in patient_frame[column].tolist():
        patient_id = normalize_patient_id(value)
        if patient_id is not None:
            patient_ids.add(patient_id)
    return patient_ids


def _patient_ids_matching_criterion(
    datasets: dict[str, pd.DataFrame],
    criterion: GroupCriterion,
) -> set[str]:
    if not criterion.is_complete():
        return set()

    frame = datasets.get(criterion.table_name)
    if frame is None:
        return set()

    patient_column = _resolve_column(
        frame,
        TABLE_PATIENT_COLUMNS[criterion.table_name],
    )
    value_column = _resolve_column(frame, criterion.column_name)
    if patient_column is None or value_column is None:
        return set()

    target_value = criterion.value.strip().casefold()
    matched: set[str] = set()
    for _, row in frame.iterrows():
        cell_value = _normalize_cell_value(row[value_column])
        if cell_value is None or cell_value.casefold() != target_value:
            continue
        patient_id = normalize_patient_id(row[patient_column])
        if patient_id is not None:
            matched.add(patient_id)
    return matched


def resolve_group_patient_ids(
    datasets: dict[str, pd.DataFrame],
    group: ComparativeGroupDefinition,
) -> set[str]:
    criteria = group.complete_criteria
    if not criteria:
        return set()

    universe = all_valid_patient_ids(datasets)
    if not universe:
        return set()

    must_sets: list[set[str]] = []
    may_sets: list[set[str]] = []
    for criterion in criteria:
        matched = _patient_ids_matching_criterion(datasets, criterion)
        if criterion.mode == CriterionMode.MUST_CONTAIN:
            must_sets.append(matched)
        else:
            may_sets.append(matched)

    if must_sets:
        group_ids = set.intersection(*must_sets) if len(must_sets) > 1 else set(must_sets[0])
        group_ids &= universe
    else:
        group_ids = set(universe)

    if may_sets:
        may_union: set[str] = set()
        for matched in may_sets:
            may_union |= matched
        group_ids &= may_union

    return group_ids


def _patient_value_for_column(
    datasets: dict[str, pd.DataFrame],
    *,
    table_name: str,
    column_name: str,
    patient_id: str,
) -> str | None:
    frame = datasets.get(table_name)
    if frame is None:
        return None

    patient_column = _resolve_column(frame, TABLE_PATIENT_COLUMNS[table_name])
    value_column = _resolve_column(frame, column_name)
    if patient_column is None or value_column is None:
        return None

    for _, row in frame.iterrows():
        row_patient_id = normalize_patient_id(row[patient_column])
        if row_patient_id != patient_id:
            continue
        value = _normalize_cell_value(row[value_column])
        if value is not None:
            return value
    return None


def is_age_analysis_target(target: AnalysisTarget) -> bool:
    return (
        target.table_name == "patient"
        and target.column_name == COMPUTED_AGE_COLUMN
    )


def _collect_values_for_validation(
    datasets: dict[str, pd.DataFrame],
    target: AnalysisTarget,
    patient_ids: set[str],
    group: ComparativeGroupDefinition,
) -> tuple[str, ...]:
    if is_age_analysis_target(target):
        from vetstats_app.analysis.detailed_comparative_analysis import _collect_age_values

        ages, _note = _collect_age_values(datasets, patient_ids, group)
        return tuple(f"{age:.4f}" for age in ages)
    return collect_target_values_for_patients(datasets, target, patient_ids)


def collect_target_values_for_patients(
    datasets: dict[str, pd.DataFrame],
    target: AnalysisTarget,
    patient_ids: set[str],
) -> tuple[str, ...]:
    if not target.is_complete():
        return ()

    values: list[str] = []
    for patient_id in sorted(patient_ids):
        value = _patient_value_for_column(
            datasets,
            table_name=target.table_name,
            column_name=target.column_name,
            patient_id=patient_id,
        )
        if value is not None:
            values.append(value)
    return tuple(values)


def _parse_numeric_value(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _values_support_mode(values: tuple[str, ...], mode: AnalysisMode) -> bool:
    if not values:
        return False
    if mode == AnalysisMode.CATEGORICAL:
        return True
    numeric_values = [_parse_numeric_value(value) for value in values]
    return sum(1 for value in numeric_values if value is not None) >= 2


def can_select_statistical_test(
    target: AnalysisTarget,
    group_1_values: tuple[str, ...],
    group_2_values: tuple[str, ...],
) -> bool:
    if not group_1_values or not group_2_values:
        return False

    if target.mode == AnalysisMode.CATEGORICAL:
        categories = set(group_1_values) | set(group_2_values)
        return len(categories) >= 2

    numeric_1 = [value for value in (_parse_numeric_value(v) for v in group_1_values) if value is not None]
    numeric_2 = [value for value in (_parse_numeric_value(v) for v in group_2_values) if value is not None]
    return len(numeric_1) >= 2 and len(numeric_2) >= 2


def build_group_count_summary(
    *,
    group_name: str,
    patient_count: int,
    total_patient_count: int,
) -> GroupCountSummary:
    share_percent = None
    if total_patient_count > 0:
        share_percent = round((patient_count / total_patient_count) * 100.0, 1)
    return GroupCountSummary(
        group_name=group_name,
        patient_count=patient_count,
        share_percent=share_percent,
    )


def validate_detailed_comparative_state(
    datasets: dict[str, pd.DataFrame],
    state: DetailedComparativeState,
) -> DetailedComparativeValidation:
    blocking: list[str] = []
    warnings: list[str] = []

    group_1_ids = resolve_group_patient_ids(datasets, state.group_1)
    group_2_ids = resolve_group_patient_ids(datasets, state.group_2)
    total_patients = len(all_valid_patient_ids(datasets))

    if not state.group_1.complete_criteria:
        blocking.append(BLOCK_NO_GROUP_1_CRITERIA)
    if not state.group_2.complete_criteria:
        blocking.append(BLOCK_NO_GROUP_2_CRITERIA)
    if not state.analysis_target.is_complete():
        blocking.append(BLOCK_NO_ANALYSIS_TARGET)

    if not blocking:
        if len(group_1_ids) == 0 or len(group_2_ids) == 0:
            blocking.append(BLOCK_ZERO_GROUP_SIZE)
        elif group_1_ids == group_2_ids:
            blocking.append(BLOCK_IDENTICAL_GROUPS)

    target = state.analysis_target
    group_1_values: tuple[str, ...] = ()
    group_2_values: tuple[str, ...] = ()
    if not blocking and target.is_complete():
        if is_age_analysis_target(target) and target.mode != AnalysisMode.NUMERIC:
            blocking.append(BLOCK_VARIABLE_MODE_MISMATCH)
        elif is_age_analysis_target(target):
            group_1_values = _collect_values_for_validation(
                datasets, target, group_1_ids, state.group_1
            )
            group_2_values = _collect_values_for_validation(
                datasets, target, group_2_ids, state.group_2
            )
            if not group_1_values or not group_2_values:
                blocking.append(BLOCK_NO_AGE_DATA)
            elif len(group_1_values) < 2 or len(group_2_values) < 2:
                blocking.append(BLOCK_INSUFFICIENT_NUMERIC_SAMPLE)
            elif not can_select_statistical_test(target, group_1_values, group_2_values):
                blocking.append(BLOCK_NO_STATISTICAL_TEST)
        else:
            group_1_values = _collect_values_for_validation(
                datasets, target, group_1_ids, state.group_1
            )
            group_2_values = _collect_values_for_validation(
                datasets, target, group_2_ids, state.group_2
            )
            if not group_1_values or not group_2_values:
                blocking.append(BLOCK_NO_VARIABLE_DATA)
            elif not _values_support_mode(group_1_values, target.mode) or not _values_support_mode(
                group_2_values, target.mode
            ):
                blocking.append(BLOCK_VARIABLE_MODE_MISMATCH)
            elif not can_select_statistical_test(target, group_1_values, group_2_values):
                blocking.append(BLOCK_NO_STATISTICAL_TEST)

    if not blocking:
        smaller = min(len(group_1_ids), len(group_2_ids))
        larger = max(len(group_1_ids), len(group_2_ids))
        if smaller < 5:
            warnings.append(WARNING_SMALL_GROUP)
        if larger > 0 and (smaller / larger) < 0.25:
            warnings.append(WARNING_IMBALANCED_GROUPS)

        if target.is_complete():
            missing_1 = len(group_1_ids) - len(group_1_values)
            missing_2 = len(group_2_ids) - len(group_2_values)
            if missing_1 + missing_2 > 0:
                missing_share = (missing_1 + missing_2) / max(len(group_1_ids) + len(group_2_ids), 1)
                if missing_share >= 0.2:
                    warnings.append(WARNING_MANY_MISSING_VALUES)

    return DetailedComparativeValidation(
        blocking_messages=tuple(blocking),
        warning_messages=tuple(warnings),
        group_1_count=len(group_1_ids),
        group_2_count=len(group_2_ids),
        total_patient_count=total_patients,
        can_analyze=not blocking,
    )

