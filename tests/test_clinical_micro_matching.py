"""Tests for shared clinical-to-micro matching."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.clinical_micro_matching import (
    match_clinical_rows_to_micro_bacteria,
)


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "date_appointment_first_before_micro": "3.01.2025",
    }
    row.update(overrides)
    return row


def _micro_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "result_ID": "001/TEST",
        "date_collect": "5.01.2025",
        "bacteria": "negative",
    }
    row.update(overrides)
    return row


def test_match_clinical_rows_to_micro_bacteria_chooses_closest_result_id() -> None:
    clinical = pd.DataFrame([_clinical_row()])
    micro = pd.DataFrame(
        [
            _micro_row(result_ID="001/TEST", date_collect="5.01.2025"),
            _micro_row(result_ID="002/TEST", date_collect="20.06.2025"),
        ]
    )

    matched, summary = match_clinical_rows_to_micro_bacteria(clinical, micro)

    assert summary.matched_pairs == 1
    assert len(matched) == 1
    assert matched.loc[0, "result_ID"] == "001/TEST"
