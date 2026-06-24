"""Integration-style tests for detailed comparative analysis launch path."""

from __future__ import annotations

from vetstats_app.analysis.detailed_comparative import (
    AnalysisMode,
    AnalysisTarget,
    BLOCK_STATISTICAL_TEST_EXECUTION_FAILED,
    ComparativeGroupDefinition,
    COMPUTED_AGE_COLUMN,
    COMPUTED_AGE_DISPLAY_LABEL,
    DetailedComparativeState,
    GroupCriterion,
    build_analysis_target,
    validate_detailed_comparative_state,
)
from vetstats_app.services.detailed_comparative_service import DetailedComparativeService


def _clinical_groups() -> tuple[ComparativeGroupDefinition, ComparativeGroupDefinition]:
    group_1 = ComparativeGroupDefinition(
        default_name="Grupa 1",
        criteria=(GroupCriterion("clinical", "type_of_ulcer", "e"),),
    )
    group_2 = ComparativeGroupDefinition(
        default_name="Grupa 2",
        criteria=(GroupCriterion("clinical", "type_of_ulcer", "s"),),
    )
    return group_1, group_2


def test_build_analysis_target_resolves_age_display_label() -> None:
    target = build_analysis_target(
        "patient",
        COMPUTED_AGE_DISPLAY_LABEL,
        "categorical",
    )
    assert target.column_name == COMPUTED_AGE_COLUMN
    assert target.mode == AnalysisMode.NUMERIC


def test_real_data_age_and_breed_comparisons_succeed() -> None:
    service = DetailedComparativeService()
    datasets = service.load_datasets()
    if "patient" not in datasets or "clinical" not in datasets:
        return

    group_1, group_2 = _clinical_groups()
    age_state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=build_analysis_target(
            "patient",
            COMPUTED_AGE_COLUMN,
            AnalysisMode.NUMERIC,
        ),
    )
    breed_state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=build_analysis_target(
            "patient",
            "breed",
            AnalysisMode.CATEGORICAL,
        ),
    )

    age_validation = validate_detailed_comparative_state(datasets, age_state)
    breed_validation = validate_detailed_comparative_state(datasets, breed_state)
    assert age_validation.can_analyze
    assert breed_validation.can_analyze

    age_result = service.analyze(age_state, datasets)
    breed_result = service.analyze(breed_state, datasets)
    assert age_result.is_success, age_result.error_message
    assert breed_result.is_success, breed_result.error_message
    assert age_result.test_result is not None
    assert breed_result.test_result is not None


def test_statistical_execution_failure_is_not_generic_when_samples_exist(
    monkeypatch,
) -> None:
    from vetstats_app.analysis import detailed_comparative_analysis as engine

    service = DetailedComparativeService()
    datasets = service.load_datasets()
    if "patient" not in datasets or "clinical" not in datasets:
        return

    group_1, group_2 = _clinical_groups()
    state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )

    def _fail_categorical_test(**_kwargs):
        return None, "synthetic scipy failure"

    monkeypatch.setattr(engine, "_select_categorical_test", _fail_categorical_test)
    result = service.analyze(state, datasets)
    assert not result.is_success
    assert result.error_message is not None
    assert result.error_message.startswith(
        BLOCK_STATISTICAL_TEST_EXECUTION_FAILED.split("{")[0]
    )
    assert "synthetic scipy failure" in result.error_message


def test_missing_scipy_returns_user_facing_message(monkeypatch) -> None:
    from vetstats_app.analysis import detailed_comparative_analysis as engine
    from vetstats_app.analysis.detailed_comparative import BLOCK_SCIPY_MISSING

    service = DetailedComparativeService()
    datasets = service.load_datasets()
    if "patient" not in datasets or "clinical" not in datasets:
        return

    group_1, group_2 = _clinical_groups()
    state = DetailedComparativeState(
        group_1=group_1,
        group_2=group_2,
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )

    monkeypatch.setattr(engine, "scipy_missing_message", lambda: BLOCK_SCIPY_MISSING)
    result = service.analyze(state, datasets)
    assert not result.is_success
    assert result.error_message == BLOCK_SCIPY_MISSING


def test_scipy_import_error_is_translated_for_test_execution(monkeypatch) -> None:
    from vetstats_app.analysis.statistical_runtime import format_statistical_runtime_error
    from vetstats_app.analysis.detailed_comparative import BLOCK_SCIPY_MISSING

    assert (
        format_statistical_runtime_error("No module named 'scipy'")
        == BLOCK_SCIPY_MISSING
    )
