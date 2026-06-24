"""Tests for clinical.csv schema, validation, and cleaning."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_sterilizer.cleaning.clinical import clean_clinical
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN, load_csv
from data_sterilizer.schemas.clinical import (
    ALLOWED_HOW_ENDED,
    REQUIRED_COLUMNS,
    is_valid_clinical_date,
    is_valid_duration,
    normalize_column_names,
)
from data_sterilizer.validation.clinical import validate_clinical


def _clinical_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame[SOURCE_ROW_COLUMN] = range(2, len(frame) + 2)
    return frame


def _valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "eye": "l",
        "type_of_ulcer": "s",
        "date_appointment_first_before_micro": "3.01.2025",
        "duration_of_problem": "2 weeks",
        "drug_used_before_micro": "tobrex",
        "farmacology_surgery": "f",
        "topical_systemic": "t",
        "EMS": "yes",
        "type_of_surgery": "x",
        "top_treatment_after": "x",
        "sys_treatment_after": "x",
        "how_ended": "good",
    }
    row.update(overrides)
    return row


def test_schema_required_columns_match_csv() -> None:
    assert "patient_ID" in REQUIRED_COLUMNS
    assert "EMS" in REQUIRED_COLUMNS
    assert len(REQUIRED_COLUMNS) == 13


def test_normalize_column_names_is_case_insensitive_for_ems_and_patient_id() -> None:
    rename_map = normalize_column_names(
        ["patient_id", "ems", "eye", "type_of_ulcer", "date_appointment_first_before_micro",
         "duration_of_problem", "drug_used_before_micro", "farmacology_surgery",
         "topical_systemic", "type_of_surgery", "top_treatment_after",
         "sys_treatment_after", "how_ended"]
    )

    assert rename_map == {"patient_id": "patient_ID", "ems": "EMS"}


def test_is_valid_clinical_date_accepts_single_digit_day_and_month() -> None:
    assert is_valid_clinical_date("3.01.2025") is True
    assert is_valid_clinical_date("31.02.2025") is False


def test_is_valid_duration_accepts_xxx_and_float_with_unit() -> None:
    assert is_valid_duration("xxx") is True
    assert is_valid_duration("2 weeks") is True
    assert is_valid_duration("1,5 months") is True
    assert is_valid_duration("4 monts") is False


def test_validate_clinical_allows_repeated_patient_id() -> None:
    rows = [_valid_row(patient_ID="1"), _valid_row(patient_ID="1", eye="r")]
    report = validate_clinical(_clinical_frame(rows))
    assert report.error_count == 0


def test_validate_clinical_checks_ulcer_type_and_eye() -> None:
    report = validate_clinical(_clinical_frame([_valid_row(eye="z", type_of_ulcer="bad")]))
    assert report.error_count == 2


def test_validate_clinical_enforces_surgery_dependency_for_farmacology_s() -> None:
    report = validate_clinical(
        _clinical_frame([_valid_row(farmacology_surgery="s", type_of_surgery="x")])
    )
    assert any("type_of_surgery is required" in issue.message for issue in report.issues)


def test_validate_clinical_enforces_treatment_dependency_for_farmacology_f() -> None:
    report = validate_clinical(
        _clinical_frame([
            _valid_row(
                farmacology_surgery="f",
                type_of_surgery="x",
                top_treatment_after="biodacyna",
                sys_treatment_after="x",
            )
        ])
    )
    assert any(issue.column == "top_treatment_after" for issue in report.issues)


def test_validate_clinical_accepts_semicolon_surgery_values() -> None:
    report = validate_clinical(
        _clinical_frame([
            _valid_row(
                farmacology_surgery="s",
                type_of_surgery="resection;pk",
                top_treatment_after="biodacyna;tropicamid",
                sys_treatment_after="x",
            )
        ])
    )
    assert report.error_count == 0


def test_validate_clinical_accepts_new_surgery_type_codes() -> None:
    for surgery_value in ("deb", "debkol", "kol", "deb;kol"):
        report = validate_clinical(
            _clinical_frame([
                _valid_row(
                    farmacology_surgery="s",
                    type_of_surgery=surgery_value,
                    top_treatment_after="biodacyna",
                    sys_treatment_after="x",
                )
            ])
        )
        assert report.error_count == 0, surgery_value


def test_validate_clinical_rejects_invalid_how_ended() -> None:
    report = validate_clinical(_clinical_frame([_valid_row(how_ended="continuation")]))
    assert report.error_count == 1
    assert report.issues[0].column == "how_ended"


def test_clean_clinical_lowercases_values_and_replaces_empty_how_ended() -> None:
    frame = _clinical_frame([
        {
            "patient_ID": "1",
            "eye": " L ",
            "type_of_ulcer": "S",
            "date_appointment_first_before_micro": "3.01.2025",
            "duration_of_problem": "2 weeks",
            "drug_used_before_micro": "TOBREX",
            "farmacology_surgery": "F",
            "topical_systemic": "TS",
            "EMS": "YES",
            "type_of_surgery": "x",
            "top_treatment_after": "x",
            "sys_treatment_after": "",
            "how_ended": "",
        }
    ])

    cleaned, report = clean_clinical(frame)

    assert cleaned.loc[0, "eye"] == "l"
    assert cleaned.loc[0, "EMS"] == "yes"
    assert cleaned.loc[0, "how_ended"] == "xxx"
    assert cleaned.loc[0, "sys_treatment_after"] == "xxx"
    assert list(cleaned.columns)[:-1] == list(REQUIRED_COLUMNS)


def test_clean_clinical_from_sample_csv_applies_global_rules() -> None:
    source = Path(__file__).resolve().parent.parent / "Data_to_check" / "clinical.csv"
    frame = load_csv(source)

    cleaned, _report = clean_clinical(frame)

    assert "EMS" in cleaned.columns
    assert cleaned["EMS"].str.lower().isin({"yes", "no", "xxx"}).all()
    assert cleaned["type_of_ulcer"].str.lower().isin({"s", "e", "p", "m", "n", "sceed", "x", "xxx"}).all()
