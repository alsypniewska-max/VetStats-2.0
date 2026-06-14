"""Validation rules for micro.csv."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.schemas.micro import (
    ALLOWED_GROWTH,
    ALLOWED_POSITIVE_SUSCEPTIBILITY,
    ALLOWED_SUSCEPTIBILITY,
    ANTIBIOTIC_COLUMNS,
    BACTERIA_COLUMN,
    DATASET_NAME,
    DATE_COLLECT_COLUMN,
    DATE_COLUMNS,
    DATE_RECEIVED_COLUMN,
    DATE_RESULT_COLUMN,
    DUPLICATE_KEY_COLUMNS,
    GROWTH_COLUMN,
    NEGATIVE_BACTERIA_VALUE,
    NOT_APPLICABLE_VALUE,
    REQUIRED_COLUMNS,
    RESULT_ID_COLUMN,
    SUSCEPTIBILITY_COLUMNS,
    is_valid_micro_date,
    normalize_column_names,
    parse_micro_date,
)
from data_sterilizer.validation.issues import Issue, Severity, ValidationReport


def validate_micro(frame: pd.DataFrame) -> ValidationReport:
    """Validate micro.csv according to the Phase 6 specification."""
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
    _validate_result_id_date_consistency(report, working)

    for row_index, row in working.iterrows():
        source_row = int(row[SOURCE_ROW_COLUMN])
        bacteria_value = str(row[BACTERIA_COLUMN]).strip().lower()
        is_negative = bacteria_value == NEGATIVE_BACTERIA_VALUE

        if bacteria_value == "":
            _add_value_error(report, source_row, BACTERIA_COLUMN, bacteria_value)

        for date_column in DATE_COLUMNS:
            date_value = str(row[date_column]).strip()
            if not is_valid_micro_date(date_value):
                _add_value_error(report, source_row, date_column, date_value)

        _validate_date_order(report, source_row, row)

        growth_value = str(row[GROWTH_COLUMN]).strip().lower()
        if growth_value not in ALLOWED_GROWTH:
            _add_value_error(report, source_row, GROWTH_COLUMN, growth_value)
        elif growth_value == NOT_APPLICABLE_VALUE and not is_negative:
            _add_value_error(
                report,
                source_row,
                GROWTH_COLUMN,
                "x is only valid when bacteria is negative",
            )

        for column in SUSCEPTIBILITY_COLUMNS:
            if column == GROWTH_COLUMN:
                continue
            value = str(row[column]).strip().lower()
            allowed = ALLOWED_SUSCEPTIBILITY if is_negative else ALLOWED_POSITIVE_SUSCEPTIBILITY
            if value not in allowed:
                _add_value_error(report, source_row, column, value)

    return report


def _validate_result_id_date_consistency(report: ValidationReport, frame: pd.DataFrame) -> None:
    for result_id, group in frame.groupby(RESULT_ID_COLUMN):
        for date_column in DATE_COLUMNS:
            values = {
                str(value).strip()
                for value in group[date_column].tolist()
                if str(value).strip()
            }
            if len(values) > 1:
                report.add(
                    Issue(
                        severity=Severity.ERROR,
                        dataset=DATASET_NAME,
                        row=None,
                        column=date_column,
                        message=(
                            f"Inconsistent {date_column} values for result_ID {result_id}"
                        ),
                    )
                )


def _validate_date_order(report: ValidationReport, source_row: int, row: pd.Series) -> None:
    result_date = parse_micro_date(str(row[DATE_RESULT_COLUMN]).strip())
    received_date = parse_micro_date(str(row[DATE_RECEIVED_COLUMN]).strip())
    collect_date = parse_micro_date(str(row[DATE_COLLECT_COLUMN]).strip())

    if None in {result_date, received_date, collect_date}:
        return

    if result_date <= received_date:
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=DATASET_NAME,
                row=source_row,
                column=DATE_RESULT_COLUMN,
                message="date_result must be later than date_received",
            )
        )

    if received_date < collect_date:
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=DATASET_NAME,
                row=source_row,
                column=DATE_RECEIVED_COLUMN,
                message="date_received must be later than or equal to date_collect",
            )
        )


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
