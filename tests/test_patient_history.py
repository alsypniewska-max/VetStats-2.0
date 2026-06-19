"""Tests for patient history treatment-duration case logic."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.patient_history import (
    TREATMENT_DURATION_CONTINUED,
    TREATMENT_DURATION_DISPLAY_COLUMN,
    TREATMENT_DURATION_NO_FOLLOWUP,
    TREATMENT_DURATION_UNAVAILABLE,
    build_patient_history_detail,
)
from vetstats_app.analysis.treatment_cases import (
    _decompose_calendar_duration,
    format_treatment_duration_text,
)


def _patient_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "patient_ID": "42",
                "name": "reks",
                "date_of_birth": "1.01.2020",
                "species": "pies",
                "breed": "mieszaniec",
                "gender": "m",
                "diseases_not_opht": "x",
                "other_diseases_opht": "x",
            }
        ]
    )


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "42",
        "eye": "l",
        "type_of_ulcer": "e",
        "date_appointment_first_before_micro": "1.09.2024",
        "duration_of_problem": "2 weeks",
        "farmacology_surgery": "f",
        "topical_systemic": "t",
        "type_of_surgery": "x",
        "how_ended": "good",
    }
    row.update(overrides)
    return row


def _empty_micro_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["patient_ID", "result_ID"])


def test_decompose_calendar_duration_example() -> None:
    from datetime import date

    months, days, total = _decompose_calendar_duration(
        date(2024, 9, 1),
        date(2025, 1, 13),
    )
    assert months == 4
    assert days == 12
    assert total == 134


def test_format_treatment_duration_good_without_date_last_appointment() -> None:
    from datetime import date

    text = format_treatment_duration_text(
        terminal_status="good",
        is_intermediate_continuation=False,
        start_date=date(2025, 1, 3),
        end_date=None,
    )
    assert text == TREATMENT_DURATION_UNAVAILABLE


def test_format_treatment_duration_same_day_good_with_date_last_appointment() -> None:
    from datetime import date

    text = format_treatment_duration_text(
        terminal_status="good",
        is_intermediate_continuation=False,
        start_date=date(2025, 1, 3),
        end_date=date(2025, 1, 3),
    )
    assert text == "0 dni (0 dni)"


def test_format_treatment_duration_enucleation_suffix() -> None:
    from datetime import date

    text = format_treatment_duration_text(
        terminal_status="enucleation",
        is_intermediate_continuation=False,
        start_date=date(2024, 9, 1),
        end_date=date(2025, 1, 13),
    )
    assert text == "4 miesiące, 12 dni (134 dni) (oko usunięto)"


def test_format_treatment_duration_continuation_terminal() -> None:
    text = format_treatment_duration_text(
        terminal_status="continuation",
        is_intermediate_continuation=False,
        start_date=None,
        end_date=None,
    )
    assert text == TREATMENT_DURATION_CONTINUED


def test_continuation_chain_good_without_date_last_appointment() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(
                date_appointment_first_before_micro="1.09.2024",
                type_of_ulcer="e",
                how_ended="continuation",
            ),
            _clinical_row(
                date_appointment_first_before_micro="1.11.2024",
                type_of_ulcer="s",
                how_ended="continuation",
            ),
            _clinical_row(
                date_appointment_first_before_micro="13.01.2025",
                type_of_ulcer="p",
                how_ended="good",
            ),
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    durations = [row[duration_index] for row in detail.clinical_rows]
    assert durations[0] == TREATMENT_DURATION_CONTINUED
    assert durations[1] == TREATMENT_DURATION_CONTINUED
    assert durations[2] == TREATMENT_DURATION_UNAVAILABLE


def test_continuation_chain_good_with_date_last_appointment_on_terminal() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(
                date_appointment_first_before_micro="1.09.2024",
                how_ended="continuation",
            ),
            _clinical_row(
                date_appointment_first_before_micro="1.11.2024",
                how_ended="continuation",
            ),
            {
                **_clinical_row(
                    date_appointment_first_before_micro="13.01.2025",
                    how_ended="good",
                ),
                "date_last_appointment": "13.01.2025",
            },
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    durations = [row[duration_index] for row in detail.clinical_rows]
    assert durations[2] == "4 miesiące, 12 dni (134 dni)"


def test_good_without_date_last_appointment_on_terminal_row() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(
                date_appointment_first_before_micro="1.01.2025",
                how_ended="good",
            ),
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    assert detail.clinical_rows[0][duration_index] == TREATMENT_DURATION_UNAVAILABLE


def test_good_uses_date_last_appointment_only_from_terminal_row() -> None:
    clinical = pd.DataFrame(
        [
            {
                **_clinical_row(
                    date_appointment_first_before_micro="1.09.2024",
                    how_ended="continuation",
                ),
                "date_last_appointment": "1.12.2024",
            },
            _clinical_row(
                date_appointment_first_before_micro="13.01.2025",
                how_ended="good",
            ),
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    durations = [row[duration_index] for row in detail.clinical_rows]
    assert durations[0] == TREATMENT_DURATION_CONTINUED
    assert durations[1] == TREATMENT_DURATION_UNAVAILABLE


def test_enucleation_with_date_last_appointment_on_terminal() -> None:
    clinical = pd.DataFrame(
        [
            {
                **_clinical_row(
                    date_appointment_first_before_micro="1.09.2024",
                    how_ended="enucleation",
                ),
                "date_last_appointment": "13.01.2025",
            }
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    assert (
        detail.clinical_rows[0][duration_index]
        == "4 miesiące, 12 dni (134 dni) (oko usunięto)"
    )


def test_good_closes_case_and_next_row_starts_new_case() -> None:
    clinical = pd.DataFrame(
        [
            {
                **_clinical_row(
                    date_appointment_first_before_micro="1.01.2025",
                    how_ended="good",
                ),
                "date_last_appointment": "1.01.2025",
            },
            _clinical_row(
                date_appointment_first_before_micro="1.06.2025",
                how_ended="no followup",
            ),
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    durations = [row[duration_index] for row in detail.clinical_rows]
    assert durations[0] == "0 dni (0 dni)"
    assert durations[1] == TREATMENT_DURATION_NO_FOLLOWUP


def test_unresolved_continuation_shows_continued_message() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(
                date_appointment_first_before_micro="1.01.2025",
                how_ended="continuation",
            ),
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    assert detail.clinical_rows[0][duration_index] == TREATMENT_DURATION_CONTINUED


def test_unresolved_continuation_with_date_last_appointment_still_continued() -> None:
    clinical = pd.DataFrame(
        [
            {
                **_clinical_row(
                    date_appointment_first_before_micro="1.09.2024",
                    how_ended="continuation",
                ),
                "date_last_appointment": "13.01.2025",
            }
        ]
    )

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None

    duration_index = detail.clinical_columns.index(TREATMENT_DURATION_DISPLAY_COLUMN)
    assert detail.clinical_rows[0][duration_index] == TREATMENT_DURATION_CONTINUED


def test_missing_date_last_appointment_column_does_not_crash() -> None:
    clinical = pd.DataFrame([_clinical_row(how_ended="good")])

    detail = build_patient_history_detail(
        "42",
        _patient_frame(),
        clinical,
        _empty_micro_frame(),
    )
    assert detail is not None
    assert "date_last_appointment" not in detail.clinical_columns
    assert TREATMENT_DURATION_DISPLAY_COLUMN in detail.clinical_columns
