"""Tests for shared treatment case engine."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.treatment_cases import (
    filter_healed_cases_with_duration,
    format_treatment_duration_text,
)


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "42",
        "eye": "l",
        "type_of_ulcer": "e",
        "date_appointment_first_before_micro": "1.09.2024",
        "date_last_appointment": "15.01.2025",
        "how_ended": "good",
    }
    row.update(overrides)
    return row


def test_filter_healed_cases_excludes_non_ulcer_rows() -> None:
    frame = pd.DataFrame(
        [
            _clinical_row(type_of_ulcer="e"),
            _clinical_row(patient_ID="43", type_of_ulcer="xxx"),
        ]
    )

    healed, summary = filter_healed_cases_with_duration(frame)

    assert len(healed) == 1
    assert summary.excluded_non_ulcer == 1
    assert summary.included_healed_with_duration == 1


def test_filter_healed_cases_requires_date_last_appointment_for_good() -> None:
    frame = pd.DataFrame(
        [
            _clinical_row(date_last_appointment="15.01.2025"),
            _clinical_row(patient_ID="43", date_last_appointment="xxx"),
        ]
    )

    healed, summary = filter_healed_cases_with_duration(frame)

    assert len(healed) == 1
    assert summary.excluded_duration_unavailable == 1


def test_format_treatment_duration_same_day_good() -> None:
    from datetime import date

    text = format_treatment_duration_text(
        terminal_status="good",
        is_intermediate_continuation=False,
        start_date=date(2025, 1, 3),
        end_date=date(2025, 1, 3),
    )
    assert text == "0 dni (0 dni)"
