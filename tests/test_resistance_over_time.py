"""Tests for dynamic yearly resistance-over-time analysis."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.resistance_over_time import (
    build_inclusion_details,
    build_summary_details,
    compute_resistance_over_time,
)


def _micro_row(*, date_collect: str, bacteria: str = "streptococcus gr g") -> dict[str, str]:
    return {
        "patient_ID": "1",
        "result_ID": "001/TEST",
        "date_collect": date_collect,
        "date_result": date_collect,
        "date_received": date_collect,
        "bacteria": bacteria,
        "growth": "heavy",
        "amikacin": "0",
    }


def test_compute_resistance_over_time_uses_observed_years_from_data() -> None:
    frame = pd.DataFrame(
        [
            _micro_row(date_collect="3.01.2023"),
            _micro_row(date_collect="10.06.2025"),
            _micro_row(date_collect="15.11.2027"),
        ]
    )

    result = compute_resistance_over_time(frame)

    assert result.is_success
    assert tuple(summary.year for summary in result.yearly_summaries) == (2023, 2025, 2027)
    assert result.exclusions.included_total == 3
    assert result.exclusions.excluded_invalid_year == 0


def test_compute_resistance_over_time_excludes_unparseable_dates() -> None:
    frame = pd.DataFrame(
        [
            _micro_row(date_collect="3.01.2025"),
            _micro_row(date_collect="nieprawidlowa-data"),
        ]
    )

    result = compute_resistance_over_time(frame)

    assert result.is_success
    assert tuple(summary.year for summary in result.yearly_summaries) == (2025,)
    assert result.exclusions.included_total == 1
    assert result.exclusions.excluded_invalid_year == 1


def test_summary_text_uses_dynamic_year_span() -> None:
    frame = pd.DataFrame(
        [
            _micro_row(date_collect="3.01.2023"),
            _micro_row(date_collect="10.06.2027"),
        ]
    )
    result = compute_resistance_over_time(frame)

    summary = build_summary_details(result)
    inclusion = build_inclusion_details(result)

    assert "2023–2027" in summary
    assert "2024–2026" not in summary
    assert "2024–2026" not in inclusion
    assert "nieprawidłową datą date_collect" in inclusion
