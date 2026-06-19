"""Tests for duration_of_problem pre-visit analysis."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.duration_of_problem_stats import (
    build_interpretation_summary,
    compute_duration_of_problem_stats,
    parse_duration_of_problem_days,
)
from vetstats_app.analysis.chart_specs import build_duration_of_problem_stats_charts


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "type_of_ulcer": "e",
        "duration_of_problem": "2 weeks",
    }
    row.update(overrides)
    return row


def test_parse_duration_of_problem_days_normalizes_case_and_commas() -> None:
    assert parse_duration_of_problem_days(" 2,5 Weeks ") == 17.5


def test_compute_duration_of_problem_stats_excludes_non_ulcer_and_invalid() -> None:
    frame = pd.DataFrame(
        [
            _clinical_row(),
            _clinical_row(patient_ID="2", type_of_ulcer="xxx"),
            _clinical_row(patient_ID="3", duration_of_problem="nieprawidlowe"),
        ]
    )

    result = compute_duration_of_problem_stats(frame)

    assert result.is_success
    assert result.total_rows == 3
    assert result.excluded_non_ulcer == 1
    assert result.excluded_invalid_duration == 1
    assert result.included_rows == 1
    assert len(result.by_ulcer_type) == 1
    assert result.by_ulcer_type[0].median_days == 14.0
    assert result.all_duration_days == (14.0,)
    assert len(result.duration_value_groups) == 1


def test_duration_of_problem_charts_include_additive_visualizations() -> None:
    frame = pd.DataFrame(
        [
            _clinical_row(),
            _clinical_row(patient_ID="2", type_of_ulcer="s", duration_of_problem="1 week"),
            _clinical_row(patient_ID="3", type_of_ulcer="e", duration_of_problem="3 weeks"),
        ]
    )

    result = compute_duration_of_problem_stats(frame)
    charts = build_duration_of_problem_stats_charts(result)
    chart_ids = {chart.chart_id for chart in charts}

    assert chart_ids == {
        "duration_of_problem_by_ulcer",
        "duration_of_problem_mean_by_ulcer",
        "duration_of_problem_mean_vs_median_by_ulcer",
        "duration_of_problem_histogram",
        "duration_of_problem_box_by_ulcer",
        "duration_of_problem_cumulative",
    }
    assert charts[0].chart_type == "bar"
    assert charts[2].chart_type == "grouped_bar"
    assert charts[3].chart_type == "histogram"
    assert charts[4].chart_type == "box"
    assert all(chart.subtitle for chart in charts)


def test_interpretation_summary_includes_mean_median_and_distribution_hints() -> None:
    frame = pd.DataFrame(
        [
            _clinical_row(duration_of_problem="1 week"),
            _clinical_row(patient_ID="2", type_of_ulcer="s", duration_of_problem="2 weeks"),
            _clinical_row(patient_ID="3", type_of_ulcer="e", duration_of_problem="8 weeks"),
        ]
    )

    result = compute_duration_of_problem_stats(frame)
    interpretation = build_interpretation_summary(result)

    assert "Mediana czasu trwania problemu" in interpretation
    assert "Średnia czasu trwania problemu" in interpretation
    assert "Najkrótszy medianowy czas" in interpretation
    assert "Najkrótszy średni czas" in interpretation
    assert "średnia" in interpretation.lower()
    assert "mediana" in interpretation.lower()
