"""Tests for micro.csv schema, validation, and cleaning."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_sterilizer.cleaning.micro import clean_micro
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN, load_csv
from data_sterilizer.schemas import micro as micro_schema
from data_sterilizer.schemas.micro import (
    ANTIBIOTIC_COLUMNS,
    REQUIRED_COLUMNS,
    normalize_column_names,
    subtract_one_day,
)
from data_sterilizer.validation.micro import validate_micro


def _micro_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame[SOURCE_ROW_COLUMN] = range(2, len(frame) + 2)
    return frame


def _valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "result_ID": "003/2025",
        "date_result": "10.01.2025",
        "date_received": "7.01.2025",
        "date_collect": "3.01.2025",
        "bacteria": "streptococcus gr g",
        "growth": "heavy",
        "amikacin": "0",
        "amoxy/clavulanic": "+++",
        "azithromycin": "+++",
        "Cephalexin": "+++",
        "Ceftriaxon": "0",
        "Ciprofloxacin": "+++",
        "Chloramfenicol": "+++",
        "Doxycycline": "+++",
        "Enrofloxacin": "+",
        "Erythromycin": "+",
        "Gentamycin": "+++",
        "Marbofloxacin": "+++",
        "Moxifloxacin": "+++",
        "Neomycin": "+++",
        "Ofloxacin": "+++",
        "Tobramycin": "+",
    }
    row.update(overrides)
    return row


def test_schema_includes_moxifloxacin_and_all_csv_antibiotics() -> None:
    assert "Moxifloxacin" in REQUIRED_COLUMNS
    assert "patient_ID" in REQUIRED_COLUMNS
    assert "result_ID" in REQUIRED_COLUMNS
    assert len(ANTIBIOTIC_COLUMNS) == 16


def test_normalize_column_names_is_case_insensitive() -> None:
    rename_map = normalize_column_names(
        ["patient_id", "result_id", "date_result", "date_received", "date_collect",
         "bacteria", "growth", "moxifloxacin", "cephalexin", "ceftriaxon",
         "ciprofloxacin", "chloramfenicol", "doxycycline", "enrofloxacin",
         "erythromycin", "gentamycin", "marbofloxacin", "neomycin", "ofloxacin",
         "tobramycin", "amikacin", "amoxy/clavulanic", "azithromycin"]
    )

    assert rename_map["patient_id"] == "patient_ID"
    assert rename_map["moxifloxacin"] == "Moxifloxacin"
    assert rename_map["cephalexin"] == "Cephalexin"


def test_subtract_one_day_preserves_unpadded_format() -> None:
    assert subtract_one_day("7.01.2025") == "6.1.2025"


def test_validate_micro_allows_repeated_patient_and_result_ids() -> None:
    rows = [_valid_row(), _valid_row(bacteria="staphylococcus sp.")]
    report = validate_micro(_micro_frame(rows))
    assert report.error_count == 0


def test_validate_micro_rejects_invalid_date_order() -> None:
    report = validate_micro(
        _micro_frame([_valid_row(date_result="3.01.2025", date_received="7.01.2025", date_collect="3.01.2025")])
    )
    assert any("date_result must be later" in issue.message for issue in report.issues)


def test_validate_micro_rejects_x_in_antibiotic_for_positive_culture() -> None:
    report = validate_micro(_micro_frame([_valid_row(amikacin="x")]))
    assert report.error_count == 1
    assert report.issues[0].column == "amikacin"


def test_validate_micro_accepts_negative_culture_with_all_x() -> None:
    row = _valid_row(bacteria="negative", growth="x")
    for column in micro_schema.ANTIBIOTIC_COLUMNS:
        row[column] = "x"
    report = validate_micro(_micro_frame([row]))
    assert report.error_count == 0


def test_clean_micro_drops_unnamed_column_and_fills_missing_date_collect() -> None:
    frame = _micro_frame([
        {
            "patient_ID": "1",
            "result_ID": "003/2025",
            "date_result": "10.01.2025",
            "date_received": "7.01.2025",
            "date_collect": "",
            "bacteria": "negative",
            "growth": "x",
            **{column: "x" for column in micro_schema.ANTIBIOTIC_COLUMNS},
            "Unnamed: 23": "",
        }
    ])

    cleaned, report = clean_micro(frame)

    assert "Unnamed: 23" not in cleaned.columns
    assert cleaned.loc[0, "date_collect"] == "6.1.2025"
    assert "Moxifloxacin" in cleaned.columns
    assert any("Unnamed: 23" in correction.message for correction in report.corrections)
    assert any("date_collect" in correction.message for correction in report.corrections)


def test_clean_micro_forces_negative_row_susceptibility_to_x() -> None:
    frame = _micro_frame([
        _valid_row(
            bacteria="negative",
            growth="heavy",
            amikacin="0",
            Moxifloxacin="+++",
        )
    ])

    cleaned, report = clean_micro(frame)

    assert cleaned.loc[0, "growth"] == "x"
    assert cleaned.loc[0, "amikacin"] == "x"
    assert cleaned.loc[0, "Moxifloxacin"] == "x"
    assert any("negative culture" in correction.message for correction in report.corrections)


def test_clean_micro_removes_duplicate_patient_result_bacteria_rows() -> None:
    duplicate = _valid_row()
    frame = _micro_frame([duplicate, duplicate.copy()])

    cleaned, report = clean_micro(frame)

    assert len(cleaned) == 1
    assert any("patient_ID, result_ID, and bacteria" in correction.message for correction in report.corrections)


def test_clean_micro_from_sample_csv_keeps_canonical_antibiotic_names() -> None:
    source = Path(__file__).resolve().parent.parent / "Data_to_check" / "micro.csv"
    frame = load_csv(source)

    cleaned, report = clean_micro(frame)

    assert "Moxifloxacin" in cleaned.columns
    assert "Unnamed: 23" not in cleaned.columns
    assert list(cleaned.columns)[:-1] == list(micro_schema.REQUIRED_COLUMNS)
    assert any("Unnamed: 23" in correction.message for correction in report.corrections)
