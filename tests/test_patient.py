"""Tests for patient.csv schema, validation, and cleaning."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_sterilizer.cleaning.patient import clean_patient
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN, load_csv
from data_sterilizer.schemas.patient import (
    ALLOWED_GENDERS,
    REQUIRED_COLUMNS,
    is_valid_date_of_birth,
    normalize_column_names,
    normalize_other_diseases_opht_tokens,
)
from data_sterilizer.validation.issues import Severity
from data_sterilizer.validation.patient import validate_patient


def _patient_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame[SOURCE_ROW_COLUMN] = range(2, len(frame) + 2)
    return frame


def test_schema_required_columns_match_csv() -> None:
    assert REQUIRED_COLUMNS == (
        "patient_ID",
        "name",
        "date_of_birth",
        "species",
        "breed",
        "gender",
        "diseases_not_opht",
        "other_diseases_opht",
    )


def test_normalize_column_names_is_case_insensitive() -> None:
    rename_map = normalize_column_names(
        ["PATIENT_ID", "Name", "date_of_birth", "species", "breed", "gender", "diseases_not_opht", "other_diseases_opht"]
    )

    assert rename_map == {
        "PATIENT_ID": "patient_ID",
        "Name": "name",
    }


def test_is_valid_date_of_birth_accepts_single_digit_day_and_month() -> None:
    assert is_valid_date_of_birth("4.01.2016") is True
    assert is_valid_date_of_birth("02.11.2015") is True
    assert is_valid_date_of_birth("31.02.2016") is False
    assert is_valid_date_of_birth("xxx") is False


def test_validate_patient_detects_duplicate_patient_id() -> None:
    frame = _patient_frame(
        [
            {
                "patient_ID": "1",
                "name": "A",
                "date_of_birth": "1.01.2020",
                "species": "dog",
                "breed": "mix",
                "gender": "M",
                "diseases_not_opht": "x",
                "other_diseases_opht": "x",
            },
            {
                "patient_ID": "1",
                "name": "B",
                "date_of_birth": "2.02.2021",
                "species": "dog",
                "breed": "mix",
                "gender": "F",
                "diseases_not_opht": "x",
                "other_diseases_opht": "x",
            },
        ]
    )

    report = validate_patient(frame)

    assert report.error_count == 2
    assert all(issue.column == "patient_ID" for issue in report.issues)


def test_validate_patient_rejects_invalid_gender() -> None:
    frame = _patient_frame(
        [
            {
                "patient_ID": "1",
                "name": "A",
                "date_of_birth": "1.01.2020",
                "species": "dog",
                "breed": "mix",
                "gender": "xxx",
                "diseases_not_opht": "x",
                "other_diseases_opht": "x",
            }
        ]
    )

    report = validate_patient(frame)

    assert report.error_count == 1
    assert report.issues[0].column == "gender"


def test_validate_patient_allows_side_markers_inside_other_diseases_text() -> None:
    frame = _patient_frame(
        [
            {
                "patient_ID": "1",
                "name": "A",
                "date_of_birth": "1.01.2020",
                "species": "dog",
                "breed": "mix",
                "gender": "M",
                "diseases_not_opht": "x",
                "other_diseases_opht": "entropium lower B",
            }
        ]
    )

    report = validate_patient(frame)

    assert report.error_count == 0


def test_validate_patient_rejects_empty_semicolon_segments() -> None:
    frame = _patient_frame(
        [
            {
                "patient_ID": "1",
                "name": "A",
                "date_of_birth": "1.01.2020",
                "species": "dog",
                "breed": "mix",
                "gender": "M",
                "diseases_not_opht": "gastric;;otitis",
                "other_diseases_opht": "x",
            }
        ]
    )

    report = validate_patient(frame)

    assert report.error_count == 1
    assert report.issues[0].column == "diseases_not_opht"


def test_normalize_other_diseases_opht_tokens_fixes_distichiasis_typo() -> None:
    assert normalize_other_diseases_opht_tokens("didtihiasis") == "distichiasis"
    assert (
        normalize_other_diseases_opht_tokens("entropium;didtihiasis;cataract")
        == "entropium;distichiasis;cataract"
    )


def test_clean_patient_fixes_other_diseases_opht_token_typo() -> None:
    frame = _patient_frame(
        [
            {
                "patient_ID": "1",
                "name": "A",
                "date_of_birth": "1.01.2020",
                "species": "dog",
                "breed": "mix",
                "gender": "M",
                "diseases_not_opht": "x",
                "other_diseases_opht": "didtihiasis;cataract",
            }
        ]
    )

    cleaned, report = clean_patient(frame)

    assert cleaned.loc[0, "other_diseases_opht"] == "distichiasis;cataract"
    assert any("other_diseases_opht" in correction.message for correction in report.corrections)


def test_clean_patient_drops_unnamed_column_and_lowercases_values() -> None:
    frame = _patient_frame(
        [
            {
                "patient_ID": "1",
                "name": " Latte ",
                "date_of_birth": "4.01.2016",
                "species": "DOG",
                "breed": "Shih Tzu",
                "gender": "M",
                "diseases_not_opht": "",
                "other_diseases_opht": "cataract R",
                "Unnamed: 8": "",
            }
        ]
    )

    cleaned, report = clean_patient(frame)

    assert "Unnamed: 8" not in cleaned.columns
    assert list(cleaned.columns)[:-1] == list(REQUIRED_COLUMNS)
    assert cleaned.loc[0, "name"] == "latte"
    assert cleaned.loc[0, "gender"] == "m"
    assert cleaned.loc[0, "diseases_not_opht"] == "xxx"
    assert cleaned.loc[0, "other_diseases_opht"] == "cataract r"
    assert any("Unnamed: 8" in correction.message for correction in report.corrections)


def test_clean_patient_removes_fully_duplicated_rows() -> None:
    row = {
        "patient_ID": "1",
        "name": "latte",
        "date_of_birth": "4.01.2016",
        "species": "dog",
        "breed": "shih tzu",
        "gender": "m",
        "diseases_not_opht": "x",
        "other_diseases_opht": "x",
    }
    frame = _patient_frame([row, row.copy()])

    cleaned, report = clean_patient(frame)

    assert len(cleaned) == 1
    assert any("duplicated" in correction.message for correction in report.corrections)


def test_clean_patient_from_sample_csv_drops_trailing_empty_column(tmp_path) -> None:
    source = Path(__file__).resolve().parent.parent / "Data_to_check" / "patient.csv"
    frame = load_csv(source)

    cleaned, report = clean_patient(frame)

    assert "Unnamed: 8" not in cleaned.columns
    assert cleaned["gender"].isin(ALLOWED_GENDERS.union({"xxx"})).all()
    assert any("Unnamed: 8" in correction.message for correction in report.corrections)
