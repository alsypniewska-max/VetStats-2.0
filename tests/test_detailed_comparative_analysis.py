"""Tests for detailed comparative statistical analysis."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.detailed_comparative import (
    AnalysisMode,
    AnalysisTarget,
    ComparativeGroupDefinition,
    COMPUTED_AGE_COLUMN,
    COMPUTED_AGE_DISPLAY_LABEL,
    CriterionMode,
    DetailedComparativeState,
    GroupCriterion,
)
from vetstats_app.analysis.detailed_comparative_analysis import (
    run_detailed_comparative_analysis,
)


def _datasets() -> dict[str, pd.DataFrame]:
    patient = pd.DataFrame(
        {
            "patient_ID": ["1", "2", "3", "4", "5", "6"],
            "species": ["dog", "dog", "dog", "cat", "cat", "cat"],
            "breed": ["lab", "mix", "beagle", "persian", "mix", "siamese"],
            "date_of_birth": [
                "1.01.2018",
                "1.01.2019",
                "1.01.2020",
                "1.01.2017",
                "1.01.2018",
                "1.01.2019",
            ],
        }
    )
    clinical = pd.DataFrame(
        {
            "patient_ID": ["1", "2", "3", "4", "5", "6"],
            "type_of_ulcer": ["s", "s", "e", "p", "p", "m"],
            "EMS": ["yes", "no", "yes", "no", "yes", "no"],
            "date_appointment_first_before_micro": [
                "1.06.2024",
                "2.06.2024",
                "3.06.2024",
                "4.06.2024",
                "5.06.2024",
                "6.06.2024",
            ],
        }
    )
    return {"patient": patient, "clinical": clinical}


def _state(
    *,
    value_1: str,
    value_2: str,
    target_column: str = "breed",
    mode: AnalysisMode = AnalysisMode.CATEGORICAL,
) -> DetailedComparativeState:
    return DetailedComparativeState(
        group_1=ComparativeGroupDefinition(
            default_name="Grupa 1",
            criteria=(
                GroupCriterion("patient", "species", value_1, CriterionMode.MUST_CONTAIN),
            ),
        ),
        group_2=ComparativeGroupDefinition(
            default_name="Grupa 2",
            criteria=(
                GroupCriterion("patient", "species", value_2, CriterionMode.MUST_CONTAIN),
            ),
        ),
        analysis_target=AnalysisTarget("patient", target_column, mode),
    )


def test_categorical_analysis_returns_test_and_table() -> None:
    result = run_detailed_comparative_analysis(_datasets(), _state(value_1="dog", value_2="cat"))
    assert result.is_success
    assert result.test_result is not None
    assert result.categorical_rows
    assert result.charts
    assert "Porównano" in result.interpretation_text


def test_numeric_analysis_uses_mann_whitney_for_skewed_counts() -> None:
    datasets = _datasets()
    datasets["patient"] = pd.DataFrame(
        {
            "patient_ID": [str(index) for index in range(1, 13)],
            "species": ["dog"] * 6 + ["cat"] * 6,
            "score": [1, 2, 2, 3, 3, 20, 4, 5, 5, 6, 6, 30],
        }
    )
    state = DetailedComparativeState(
        group_1=ComparativeGroupDefinition(
            default_name="Grupa 1",
            criteria=(GroupCriterion("patient", "species", "dog"),),
        ),
        group_2=ComparativeGroupDefinition(
            default_name="Grupa 2",
            criteria=(GroupCriterion("patient", "species", "cat"),),
        ),
        analysis_target=AnalysisTarget("patient", "score", AnalysisMode.NUMERIC),
    )
    result = run_detailed_comparative_analysis(datasets, state)
    assert result.is_success
    assert result.test_result is not None
    assert result.numeric_rows
    assert result.test_result.test_name in {
        "Mann–Whitney U",
        "test t Studenta (Welcha)",
    }


def test_breed_target_does_not_use_age_computation() -> None:
    result = run_detailed_comparative_analysis(_datasets(), _state(value_1="dog", value_2="cat"))
    assert result.is_success
    assert result.variable_label == "patient.breed"
    assert not result.age_reference_date_note
    assert "Wiek obliczono" not in result.group_description_text


def test_computed_age_target_uses_dynamic_age_values() -> None:
    state = _state(
        value_1="dog",
        value_2="cat",
        target_column=COMPUTED_AGE_COLUMN,
        mode=AnalysisMode.NUMERIC,
    )
    result = run_detailed_comparative_analysis(_datasets(), state)
    assert result.is_success
    assert result.variable_label == f"patient.{COMPUTED_AGE_DISPLAY_LABEL}"
    assert result.numeric_rows
    assert result.age_reference_date_note
    assert "Jednostka analizy wieku" in result.group_description_text


def _clinical_ulcer_state(
    *,
    ulcer_1: str,
    ulcer_2: str,
) -> DetailedComparativeState:
    return DetailedComparativeState(
        group_1=ComparativeGroupDefinition(
            default_name="Grupa 1",
            criteria=(
                GroupCriterion("clinical", "type_of_ulcer", ulcer_1, CriterionMode.MUST_CONTAIN),
            ),
        ),
        group_2=ComparativeGroupDefinition(
            default_name="Grupa 2",
            criteria=(
                GroupCriterion("clinical", "type_of_ulcer", ulcer_2, CriterionMode.MUST_CONTAIN),
            ),
        ),
        analysis_target=AnalysisTarget("patient", COMPUTED_AGE_COLUMN, AnalysisMode.NUMERIC),
    )


def _clinical_ulcer_datasets() -> dict[str, pd.DataFrame]:
    patient_rows = [
        ("e1", "1.01.2018"),
        ("e2", "1.02.2018"),
        ("e3", "1.03.2018"),
        ("e4", "1.04.2018"),
        ("s1", "1.01.2019"),
        ("s2", "1.02.2019"),
        ("s3", "1.03.2019"),
        ("s4", "1.04.2019"),
    ]
    patient = pd.DataFrame(
        {
            "patient_ID": [row[0] for row in patient_rows],
            "date_of_birth": [row[1] for row in patient_rows],
        }
    )
    clinical_rows = [
        ("e1", "e", "1.06.2024"),
        ("e2", "e", "2.06.2024"),
        ("e3", "e", "3.06.2024"),
        ("e4", "e", "4.06.2024"),
        ("s1", "s", "11.06.2024"),
        ("s2", "s", "12.06.2024"),
        ("s3", "s", "13.06.2024"),
        ("s4", "s", "14.06.2024"),
    ]
    clinical = pd.DataFrame(
        {
            "patient_ID": [row[0] for row in clinical_rows],
            "type_of_ulcer": [row[1] for row in clinical_rows],
            "date_appointment_first_before_micro": [row[2] for row in clinical_rows],
        }
    )
    return {"patient": patient, "clinical": clinical}


def test_clinical_epithelial_vs_stromal_age_comparison_succeeds() -> None:
    result = run_detailed_comparative_analysis(
        _clinical_ulcer_datasets(),
        _clinical_ulcer_state(ulcer_1="e", ulcer_2="s"),
    )
    assert result.is_success
    assert result.test_result is not None
    assert len(result.numeric_rows) == 2
    assert result.group_1_with_data == 4
    assert result.group_2_with_data == 4
    assert result.test_result.test_name in {
        "Mann–Whitney U",
        "test t Studenta (Welcha)",
    }
    assert "rekordu clinical" in result.age_reference_date_note


def test_clinical_age_comparison_reports_missing_age_data() -> None:
    datasets = _clinical_ulcer_datasets()
    datasets["patient"] = datasets["patient"].drop(columns=["date_of_birth"])
    result = run_detailed_comparative_analysis(
        datasets,
        _clinical_ulcer_state(ulcer_1="e", ulcer_2="s"),
    )
    assert not result.is_success
    from vetstats_app.analysis.detailed_comparative import BLOCK_NO_AGE_DATA

    assert result.error_message == BLOCK_NO_AGE_DATA
