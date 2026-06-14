"""Validation rules for patient.csv."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.schemas.patient import (
    ALLOWED_GENDERS,
    DATASET_NAME,
    DATE_OF_BIRTH_COLUMN,
    DISEASES_NOT_OPHT_COLUMN,
    GENDER_COLUMN,
    OTHER_DISEASES_OPHT_COLUMN,
    PATIENT_ID_COLUMN,
    REQUIRED_COLUMNS,
    is_valid_date_of_birth,
    normalize_column_names,
)
from data_sterilizer.validation.issues import Issue, Severity, ValidationReport


def validate_patient(frame: pd.DataFrame) -> ValidationReport:
    """Validate patient.csv according to the Phase 6 specification."""
    report = ValidationReport()
    columns = list(frame.columns)
    rename_map = normalize_column_names(columns)
    effective_columns = {rename_map.get(column, column) for column in columns if column != SOURCE_ROW_COLUMN}

    for required in REQUIRED_COLUMNS:
        if required.lower() not in {column.lower() for column in effective_columns}:
            report.add(
                Issue(
                    severity=Severity.ERROR,
                    dataset=DATASET_NAME,
                    row=None,
                    column=required,
                    message=f"Missing required column: {required}",
                )
            )

    if report.has_errors():
        return report

    working = frame.rename(columns=rename_map)
    data_columns = [column for column in REQUIRED_COLUMNS if column in working.columns]

    duplicate_ids = working[working.duplicated(subset=[PATIENT_ID_COLUMN], keep=False)][PATIENT_ID_COLUMN].unique()
    if len(duplicate_ids):
        for patient_id in duplicate_ids:
            rows = working.index[working[PATIENT_ID_COLUMN] == patient_id].tolist()
            for row_index in rows:
                source_row = int(working.at[row_index, SOURCE_ROW_COLUMN])
                report.add(
                    Issue(
                        severity=Severity.ERROR,
                        dataset=DATASET_NAME,
                        row=source_row,
                        column=PATIENT_ID_COLUMN,
                        message=f"Duplicate patient_ID: {patient_id}",
                    )
                )

    for row_index, row in working.iterrows():
        source_row = int(row[SOURCE_ROW_COLUMN])

        date_value = str(row[DATE_OF_BIRTH_COLUMN]).strip()
        if not is_valid_date_of_birth(date_value):
            report.add(
                Issue(
                    severity=Severity.ERROR,
                    dataset=DATASET_NAME,
                    row=source_row,
                    column=DATE_OF_BIRTH_COLUMN,
                    message=f"Invalid date_of_birth format or value: {date_value}",
                )
            )

        gender_value = str(row[GENDER_COLUMN]).strip().lower()
        if gender_value not in ALLOWED_GENDERS:
            report.add(
                Issue(
                    severity=Severity.ERROR,
                    dataset=DATASET_NAME,
                    row=source_row,
                    column=GENDER_COLUMN,
                    message=f"Invalid gender value: {gender_value}",
                )
            )

        _validate_semicolon_field(
            report,
            source_row=source_row,
            column=DISEASES_NOT_OPHT_COLUMN,
            value=str(row[DISEASES_NOT_OPHT_COLUMN]).strip(),
        )
        _validate_semicolon_field(
            report,
            source_row=source_row,
            column=OTHER_DISEASES_OPHT_COLUMN,
            value=str(row[OTHER_DISEASES_OPHT_COLUMN]).strip(),
        )

    return report


def _validate_semicolon_field(
    report: ValidationReport,
    *,
    source_row: int,
    column: str,
    value: str,
) -> None:
    if ";" not in value:
        return

    parts = [part.strip() for part in value.split(";")]
    if any(part == "" for part in parts):
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=DATASET_NAME,
                row=source_row,
                column=column,
                message="Semicolon-separated values must not contain empty segments",
            )
        )
