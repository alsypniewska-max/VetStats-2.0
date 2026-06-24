"""Tests for detailed comparative group building and validation."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.detailed_comparative import (
    BLOCK_INSUFFICIENT_NUMERIC_SAMPLE,
    BLOCK_NO_AGE_DATA,
    BLOCK_IDENTICAL_GROUPS,
    BLOCK_NO_ANALYSIS_TARGET,
    BLOCK_NO_GROUP_1_CRITERIA,
    BLOCK_ZERO_GROUP_SIZE,
    AnalysisMode,
    AnalysisTarget,
    ComparativeGroupDefinition,
    COMPUTED_AGE_COLUMN,
    COMPUTED_AGE_DISPLAY_LABEL,
    CriterionMode,
    DetailedComparativeState,
    GroupCriterion,
    default_detailed_comparative_state,
    list_analysis_target_columns,
    mirror_group_2_structure,
    resolve_group_patient_ids,
    validate_detailed_comparative_state,
)


def _datasets() -> dict[str, pd.DataFrame]:
    patient = pd.DataFrame(
        {
            "patient_ID": ["1", "2", "3", "4"],
            "species": ["dog", "dog", "cat", "cat"],
            "breed": ["lab", "mix", "persian", "mix"],
        }
    )
    clinical = pd.DataFrame(
        {
            "patient_ID": ["1", "1", "2", "3"],
            "type_of_ulcer": ["s", "e", "s", "p"],
            "EMS": ["yes", "no", "yes", "no"],
        }
    )
    micro = pd.DataFrame(
        {
            "patient_ID": ["1", "2", "4"],
            "bacteria": ["staph", "strep", "ecoli"],
        }
    )
    return {"patient": patient, "clinical": clinical, "micro": micro}


def _group_with_criterion(
    *,
    default_name: str,
    table_name: str,
    column_name: str,
    value: str,
) -> ComparativeGroupDefinition:
    return ComparativeGroupDefinition(
        default_name=default_name,
        criteria=(
            GroupCriterion(
                table_name=table_name,
                column_name=column_name,
                value=value,
                mode=CriterionMode.MUST_CONTAIN,
            ),
        ),
    )


def test_resolve_group_patient_ids_from_patient_table() -> None:
    datasets = _datasets()
    group = _group_with_criterion(
        default_name="Grupa 1",
        table_name="patient",
        column_name="species",
        value="dog",
    )
    assert resolve_group_patient_ids(datasets, group) == {"1", "2"}


def test_resolve_group_patient_ids_from_clinical_table() -> None:
    datasets = _datasets()
    group = _group_with_criterion(
        default_name="Grupa 1",
        table_name="clinical",
        column_name="EMS",
        value="yes",
    )
    assert resolve_group_patient_ids(datasets, group) == {"1", "2"}


def test_mirror_group_2_copies_structure_and_preserves_values() -> None:
    group_1 = ComparativeGroupDefinition(
        default_name="Grupa 1",
        criteria=(
            GroupCriterion("patient", "species", "dog"),
            GroupCriterion("clinical", "EMS", "yes"),
        ),
    )
    group_2 = ComparativeGroupDefinition(
        default_name="Grupa 2",
        criteria=(
            GroupCriterion("patient", "species", "cat", mode=CriterionMode.MAY_CONTAIN),
        ),
    )
    mirrored = mirror_group_2_structure(group_1, group_2)
    assert len(mirrored.criteria) == 2
    assert mirrored.criteria[0].table_name == "patient"
    assert mirrored.criteria[0].column_name == "species"
    assert mirrored.criteria[0].value == "cat"
    assert mirrored.criteria[0].mode == CriterionMode.MUST_CONTAIN
    assert mirrored.criteria[1].table_name == "clinical"
    assert mirrored.criteria[1].column_name == "EMS"
    assert mirrored.criteria[1].value == ""


def test_validation_blocks_missing_criteria_and_identical_groups() -> None:
    datasets = _datasets()
    group = _group_with_criterion(
        default_name="Grupa 1",
        table_name="patient",
        column_name="species",
        value="dog",
    )
    state = DetailedComparativeState(
        group_1=ComparativeGroupDefinition(default_name="Grupa 1"),
        group_2=group,
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )
    validation = validate_detailed_comparative_state(datasets, state)
    assert BLOCK_NO_GROUP_1_CRITERIA in validation.blocking_messages
    assert not validation.can_analyze

    same_group_state = DetailedComparativeState(
        group_1=group,
        group_2=group,
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )
    validation_same = validate_detailed_comparative_state(datasets, same_group_state)
    assert BLOCK_IDENTICAL_GROUPS in validation_same.blocking_messages


def test_validation_allows_distinct_groups_with_target_data() -> None:
    datasets = _datasets()
    group_1 = _group_with_criterion(
        default_name="Grupa 1",
        table_name="patient",
        column_name="species",
        value="dog",
    )
    group_2 = _group_with_criterion(
        default_name="Grupa 2",
        table_name="patient",
        column_name="species",
        value="cat",
    )
    state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )
    validation = validate_detailed_comparative_state(datasets, state)
    assert validation.can_analyze
    assert validation.group_1_count == 2
    assert validation.group_2_count == 2


def test_validation_blocks_zero_group_size() -> None:
    datasets = _datasets()
    group_1 = _group_with_criterion(
        default_name="Grupa 1",
        table_name="patient",
        column_name="species",
        value="dog",
    )
    group_2 = _group_with_criterion(
        default_name="Grupa 2",
        table_name="patient",
        column_name="species",
        value="rabbit",
    )
    state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )
    validation = validate_detailed_comparative_state(datasets, state)
    assert BLOCK_ZERO_GROUP_SIZE in validation.blocking_messages


def test_default_state_requires_explicit_analysis_target() -> None:
    validation = validate_detailed_comparative_state(_datasets(), default_detailed_comparative_state())
    assert BLOCK_NO_ANALYSIS_TARGET in validation.blocking_messages
    assert not validation.can_analyze


def test_analysis_target_columns_exclude_date_of_birth_and_offer_computed_age() -> None:
    datasets = _datasets()
    options = dict(list_analysis_target_columns(datasets, "patient"))
    assert "date_of_birth" not in options
    assert options[COMPUTED_AGE_COLUMN] == COMPUTED_AGE_DISPLAY_LABEL
    assert "breed" in options.values()


def test_validation_allows_clinical_and_micro_targets() -> None:
    datasets = _datasets()
    group_1 = _group_with_criterion(
        default_name="Grupa 1",
        table_name="patient",
        column_name="species",
        value="dog",
    )
    group_2 = _group_with_criterion(
        default_name="Grupa 2",
        table_name="patient",
        column_name="species",
        value="cat",
    )
    clinical_state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("clinical", "EMS", AnalysisMode.CATEGORICAL),
    )
    micro_state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("micro", "bacteria", AnalysisMode.CATEGORICAL),
    )
    assert validate_detailed_comparative_state(datasets, clinical_state).can_analyze
    assert validate_detailed_comparative_state(datasets, micro_state).can_analyze


def test_validation_reports_insufficient_age_sample_for_small_clinical_group() -> None:
    datasets = _datasets()
    datasets["patient"] = pd.DataFrame(
        {
            "patient_ID": ["1", "2", "3", "4"],
            "species": ["dog", "dog", "cat", "cat"],
            "breed": ["lab", "mix", "persian", "mix"],
            "date_of_birth": [
                "1.01.2018",
                "1.01.2019",
                "1.01.2020",
                "1.01.2017",
            ],
        }
    )
    datasets["clinical"] = pd.DataFrame(
        {
            "patient_ID": ["1", "2", "3", "4"],
            "type_of_ulcer": ["s", "e", "s", "p"],
            "EMS": ["yes", "no", "yes", "no"],
            "date_appointment_first_before_micro": [
                "1.06.2024",
                "2.06.2024",
                "3.06.2024",
                "4.06.2024",
            ],
        }
    )
    group_1 = _group_with_criterion(
        default_name="Grupa 1",
        table_name="clinical",
        column_name="type_of_ulcer",
        value="e",
    )
    group_2 = _group_with_criterion(
        default_name="Grupa 2",
        table_name="clinical",
        column_name="type_of_ulcer",
        value="s",
    )
    state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("patient", COMPUTED_AGE_COLUMN, AnalysisMode.NUMERIC),
    )
    validation = validate_detailed_comparative_state(datasets, state)
    assert BLOCK_INSUFFICIENT_NUMERIC_SAMPLE in validation.blocking_messages
    assert BLOCK_NO_AGE_DATA not in validation.blocking_messages
