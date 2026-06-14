"""Validation rules for clinical.csv."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.schemas.clinical import (
    ALLOWED_DRUG_SENTINELS,
    ALLOWED_EMS,
    ALLOWED_EYES,
    ALLOWED_FARMACOLOGY,
    ALLOWED_HOW_ENDED,
    ALLOWED_SURGERY_TYPES,
    ALLOWED_TOPICAL_SYSTEMIC,
    ALLOWED_ULCER_TYPES,
    DATASET_NAME,
    DATE_APPOINTMENT_COLUMN,
    DRUG_BEFORE_MICRO_COLUMN,
    DURATION_COLUMN,
    EMS_COLUMN,
    EYE_COLUMN,
    FARMACOLOGY_SURGERY_COLUMN,
    HOW_ENDED_COLUMN,
    NOT_APPLICABLE_VALUE,
    REQUIRED_COLUMNS,
    SYS_TREATMENT_COLUMN,
    TOP_TREATMENT_COLUMN,
    TOPICAL_SYSTEMIC_COLUMN,
    TYPE_OF_SURGERY_COLUMN,
    TYPE_OF_ULCER_COLUMN,
    UNKNOWN_VALUE,
    is_valid_clinical_date,
    is_valid_duration,
    normalize_column_names,
)
from data_sterilizer.validation.issues import Issue, Severity, ValidationReport


def validate_clinical(frame: pd.DataFrame) -> ValidationReport:
    """Validate clinical.csv according to the Phase 6 specification."""
    report = ValidationReport()
    columns = list(frame.columns)
    rename_map = normalize_column_names(columns)
    effective_columns = {
        rename_map.get(column, column) for column in columns if column != SOURCE_ROW_COLUMN
    }

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

    for row_index, row in working.iterrows():
        source_row = int(row[SOURCE_ROW_COLUMN])

        eye_value = str(row[EYE_COLUMN]).strip().lower()
        if eye_value not in ALLOWED_EYES:
            _add_value_error(report, source_row, EYE_COLUMN, eye_value)

        ulcer_value = str(row[TYPE_OF_ULCER_COLUMN]).strip().lower()
        if ulcer_value not in ALLOWED_ULCER_TYPES:
            _add_value_error(report, source_row, TYPE_OF_ULCER_COLUMN, ulcer_value)

        date_value = str(row[DATE_APPOINTMENT_COLUMN]).strip()
        if not is_valid_clinical_date(date_value):
            _add_value_error(report, source_row, DATE_APPOINTMENT_COLUMN, date_value)

        duration_value = str(row[DURATION_COLUMN]).strip().lower()
        if not is_valid_duration(duration_value):
            _add_value_error(report, source_row, DURATION_COLUMN, duration_value)

        drug_value = str(row[DRUG_BEFORE_MICRO_COLUMN]).strip().lower()
        _validate_semicolon_field(report, source_row, DRUG_BEFORE_MICRO_COLUMN, drug_value)

        farm_value = str(row[FARMACOLOGY_SURGERY_COLUMN]).strip().lower()
        if farm_value not in ALLOWED_FARMACOLOGY:
            _add_value_error(report, source_row, FARMACOLOGY_SURGERY_COLUMN, farm_value)

        topical_systemic_value = str(row[TOPICAL_SYSTEMIC_COLUMN]).strip().lower()
        if topical_systemic_value not in ALLOWED_TOPICAL_SYSTEMIC:
            _add_value_error(report, source_row, TOPICAL_SYSTEMIC_COLUMN, topical_systemic_value)

        ems_value = str(row[EMS_COLUMN]).strip().lower()
        if ems_value not in ALLOWED_EMS:
            _add_value_error(report, source_row, EMS_COLUMN, ems_value)

        surgery_value = str(row[TYPE_OF_SURGERY_COLUMN]).strip().lower()
        _validate_type_of_surgery(report, source_row, surgery_value)
        _validate_surgery_dependencies(
            report,
            source_row=source_row,
            farmacology=farm_value,
            surgery_value=surgery_value,
        )

        top_treatment_value = str(row[TOP_TREATMENT_COLUMN]).strip().lower()
        sys_treatment_value = str(row[SYS_TREATMENT_COLUMN]).strip().lower()
        _validate_semicolon_field(report, source_row, TOP_TREATMENT_COLUMN, top_treatment_value)
        _validate_semicolon_field(report, source_row, SYS_TREATMENT_COLUMN, sys_treatment_value)
        _validate_treatment_dependencies(
            report,
            source_row=source_row,
            farmacology=farm_value,
            top_treatment=top_treatment_value,
            sys_treatment=sys_treatment_value,
        )

        how_ended_value = str(row[HOW_ENDED_COLUMN]).strip().lower()
        if how_ended_value not in ALLOWED_HOW_ENDED:
            _add_value_error(report, source_row, HOW_ENDED_COLUMN, how_ended_value)

    return report


def _add_value_error(
    report: ValidationReport,
    source_row: int,
    column: str,
    value: str,
) -> None:
    report.add(
        Issue(
            severity=Severity.ERROR,
            dataset=DATASET_NAME,
            row=source_row,
            column=column,
            message=f"Invalid value: {value}",
        )
    )


def _validate_semicolon_field(
    report: ValidationReport,
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


def _validate_type_of_surgery(
    report: ValidationReport,
    source_row: int,
    value: str,
) -> None:
    if value in {NOT_APPLICABLE_VALUE, UNKNOWN_VALUE}:
        return

    parts = [part.strip() for part in value.split(";")]
    if not parts or len(parts) > 2:
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=DATASET_NAME,
                row=source_row,
                column=TYPE_OF_SURGERY_COLUMN,
                message=f"Invalid type_of_surgery structure: {value}",
            )
        )
        return

    for part in parts:
        if part not in ALLOWED_SURGERY_TYPES:
            _add_value_error(report, source_row, TYPE_OF_SURGERY_COLUMN, value)


def _validate_surgery_dependencies(
    report: ValidationReport,
    *,
    source_row: int,
    farmacology: str,
    surgery_value: str,
) -> None:
    if farmacology == "f" and surgery_value != NOT_APPLICABLE_VALUE:
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=DATASET_NAME,
                row=source_row,
                column=TYPE_OF_SURGERY_COLUMN,
                message="type_of_surgery must be x when farmacology_surgery is f",
            )
        )

    if farmacology == "s" and surgery_value in {NOT_APPLICABLE_VALUE, UNKNOWN_VALUE, ""}:
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=DATASET_NAME,
                row=source_row,
                column=TYPE_OF_SURGERY_COLUMN,
                message="type_of_surgery is required when farmacology_surgery is s",
            )
        )


def _validate_treatment_dependencies(
    report: ValidationReport,
    *,
    source_row: int,
    farmacology: str,
    top_treatment: str,
    sys_treatment: str,
) -> None:
    if farmacology == "f":
        if top_treatment != NOT_APPLICABLE_VALUE:
            report.add(
                Issue(
                    severity=Severity.ERROR,
                    dataset=DATASET_NAME,
                    row=source_row,
                    column=TOP_TREATMENT_COLUMN,
                    message="top_treatment_after must be x when farmacology_surgery is f",
                )
            )
        if sys_treatment != NOT_APPLICABLE_VALUE:
            report.add(
                Issue(
                    severity=Severity.ERROR,
                    dataset=DATASET_NAME,
                    row=source_row,
                    column=SYS_TREATMENT_COLUMN,
                    message="sys_treatment_after must be x when farmacology_surgery is f",
                )
            )
