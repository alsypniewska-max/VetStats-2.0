"""Tests for monthly micro swab distribution."""

from __future__ import annotations

from datetime import date

import pandas as pd

from vetstats_app.analysis.chart_specs import build_micro_monthly_distribution_charts
from vetstats_app.analysis.micro_monthly_distribution import (
    SwabCollectionRecord,
    build_monthly_distribution,
    compute_micro_monthly_distribution,
)


def _micro_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "result_ID": "001/TEST",
        "date_collect": "3.01.2025",
    }
    row.update(overrides)
    return row


def test_build_monthly_distribution_counts_distinct_result_id_per_month() -> None:
    records = (
        SwabCollectionRecord(collect_date=date(2025, 1, 3), result_id="001/TEST"),
        SwabCollectionRecord(collect_date=date(2025, 1, 10), result_id="001/TEST"),
        SwabCollectionRecord(collect_date=date(2025, 6, 15), result_id="002/TEST"),
    )
    distribution = build_monthly_distribution(records, year=2025)

    assert len(distribution.months) == 12
    assert distribution.months[0].count == 1
    assert distribution.months[5].count == 1
    assert distribution.months[1].count == 0
    assert distribution.total_swabs == 2


def test_build_monthly_distribution_combined_dedupes_same_result_id_in_month() -> None:
    records = (
        SwabCollectionRecord(collect_date=date(2024, 3, 1), result_id="001/TEST"),
        SwabCollectionRecord(collect_date=date(2025, 3, 15), result_id="001/TEST"),
        SwabCollectionRecord(collect_date=date(2025, 3, 20), result_id="002/TEST"),
    )
    distribution = build_monthly_distribution(records)

    assert distribution.months[2].count == 2
    assert distribution.total_swabs == 2


def test_build_monthly_distribution_combined_counts_one_result_id_once_per_month() -> None:
    records = (
        SwabCollectionRecord(collect_date=date(2024, 3, 1), result_id="001/TEST"),
        SwabCollectionRecord(collect_date=date(2025, 3, 15), result_id="001/TEST"),
    )
    distribution = build_monthly_distribution(records)

    assert distribution.months[2].count == 1
    assert distribution.total_swabs == 1


def test_compute_micro_monthly_distribution_builds_per_year_and_combined() -> None:
    frame = pd.DataFrame(
        [
            _micro_row(date_collect="3.01.2024"),
            _micro_row(result_ID="002/TEST", date_collect="10.06.2025"),
            _micro_row(result_ID="003/TEST", date_collect="15.11.2025"),
            _micro_row(result_ID="004/TEST", date_collect="xxx"),
            _micro_row(result_ID="005/TEST", date_collect="1.02.2025", bacteria="a"),
            _micro_row(result_ID="005/TEST", date_collect="1.02.2025", bacteria="b"),
        ]
    )

    result = compute_micro_monthly_distribution(frame)

    assert result.is_success
    assert result.observed_years == (2024, 2025)
    assert len(result.yearly_distributions) == 2
    assert result.included_swabs == 4
    assert result.combined_distribution.total_swabs == 4
    assert result.excluded_invalid_date_collect == 1
    assert result.excluded_missing_result_id == 0
    assert result.yearly_distributions[1].months[1].count == 1


def test_compute_micro_monthly_distribution_excludes_missing_result_id() -> None:
    frame = pd.DataFrame(
        [
            _micro_row(result_ID="xxx", date_collect="3.01.2025"),
            _micro_row(result_ID="002/TEST", date_collect="4.01.2025"),
        ]
    )

    result = compute_micro_monthly_distribution(frame)

    assert result.included_swabs == 1
    assert result.excluded_missing_result_id == 1


def test_micro_monthly_charts_include_each_year_and_combined() -> None:
    frame = pd.DataFrame(
        [
            _micro_row(date_collect="3.01.2024"),
            _micro_row(result_ID="002/TEST", date_collect="10.06.2025"),
        ]
    )
    result = compute_micro_monthly_distribution(frame)
    charts = build_micro_monthly_distribution_charts(result)

    assert len(charts) == 3
    assert all(chart.chart_type == "bar" for chart in charts)
    assert all(len(chart.labels) == 12 for chart in charts)
