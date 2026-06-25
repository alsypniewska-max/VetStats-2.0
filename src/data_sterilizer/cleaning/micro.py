"""Cleaning rules for micro.csv."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.cleaning.common import (
    drop_fully_duplicated_rows,
    drop_fully_empty_rows,
    lowercase_text,
    replace_empty_cells,
    trim_whitespace,
)
from data_sterilizer.cleaning.report import CleaningReport, Correction
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.schemas.micro import (
    ANTIBIOTIC_COLUMNS,
    BACTERIA_COLUMN,
    DATASET_NAME,
    DATE_COLLECT_COLUMN,
    DATE_COLUMNS,
    DATE_RECEIVED_COLUMN,
    DUPLICATE_KEY_COLUMNS,
    EMPTY_VALUE_REPLACEMENT,
    GLOBAL_EMPTY_COLUMNS,
    GROWTH_COLUMN,
    NEGATIVE_BACTERIA_VALUE,
    NOT_APPLICABLE_VALUE,
    REQUIRED_COLUMNS,
    RESULT_ID_COLUMN,
    SUSCEPTIBILITY_COLUMNS,
    is_missing_date_collect,
    is_trailing_empty_column,
    is_valid_micro_date,
    normalize_column_names,
    parse_result_id_year,
    replace_micro_date_year,
    subtract_one_day,
)


def clean_micro(frame: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Apply micro-specific and global cleaning rules."""
    report = CleaningReport()
    cleaned = frame.copy()

    rename_map = normalize_column_names(list(cleaned.columns))
    if rename_map:
        cleaned = cleaned.rename(columns=rename_map)
        renamed = ", ".join(f"{old} -> {new}" for old, new in rename_map.items())
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=f"Normalized column names to canonical CSV names: {renamed}",
            )
        )

    dropped_columns = [
        column
        for column in cleaned.columns
        if column != SOURCE_ROW_COLUMN and is_trailing_empty_column(column)
    ]
    if dropped_columns:
        cleaned = cleaned.drop(columns=dropped_columns)
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message="Dropped trailing empty column(s): " + ", ".join(dropped_columns),
            )
        )

    text_columns = [column for column in REQUIRED_COLUMNS if column in cleaned.columns]
    cleaned = trim_whitespace(cleaned, text_columns)
    cleaned = lowercase_text(cleaned, text_columns)

    filled_dates = 0
    for row_index, row in cleaned.iterrows():
        collect_value = str(row[DATE_COLLECT_COLUMN]).strip()
        received_value = str(row[DATE_RECEIVED_COLUMN]).strip()
        if is_missing_date_collect(collect_value):
            replacement = subtract_one_day(received_value)
            if replacement is not None:
                cleaned.at[row_index, DATE_COLLECT_COLUMN] = replacement
                filled_dates += 1
    if filled_dates:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=f"Filled {filled_dates} missing date_collect value(s) from date_received minus 1 day",
            )
        )

    year_corrections = _sync_date_years_with_result_id(cleaned)
    if year_corrections:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=(
                    "Aligned micro date year(s) with result_ID in "
                    f"{year_corrections} row(s)"
                ),
            )
        )

    cleaned = replace_empty_cells(
        cleaned,
        [column for column in GLOBAL_EMPTY_COLUMNS if column in cleaned.columns],
        EMPTY_VALUE_REPLACEMENT,
    )
    cleaned = replace_empty_cells(
        cleaned,
        [column for column in SUSCEPTIBILITY_COLUMNS if column in cleaned.columns],
        NOT_APPLICABLE_VALUE,
    )

    corrected_negative_rows = 0
    for row_index, row in cleaned.iterrows():
        if str(row[BACTERIA_COLUMN]).strip().lower() != NEGATIVE_BACTERIA_VALUE:
            continue

        changed = False
        for column in SUSCEPTIBILITY_COLUMNS:
            if str(row[column]).strip().lower() != NOT_APPLICABLE_VALUE:
                cleaned.at[row_index, column] = NOT_APPLICABLE_VALUE
                changed = True
        if changed:
            corrected_negative_rows += 1

    if corrected_negative_rows:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=(
                    "Set growth and antibiotic columns to x for "
                    f"{corrected_negative_rows} negative culture row(s)"
                ),
            )
        )

    before_rows = len(cleaned)
    cleaned = drop_fully_empty_rows(cleaned, text_columns)
    removed_empty_rows = before_rows - len(cleaned)
    if removed_empty_rows:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=f"Removed {removed_empty_rows} fully empty row(s)",
            )
        )

    duplicate_columns = [column for column in DUPLICATE_KEY_COLUMNS if column in cleaned.columns]
    before_rows = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=duplicate_columns, keep="first")
    removed_key_duplicates = before_rows - len(cleaned)
    if removed_key_duplicates:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=(
                    "Removed "
                    f"{removed_key_duplicates} duplicate row(s) with the same "
                    "patient_ID, result_ID, and bacteria"
                ),
            )
        )

    before_rows = len(cleaned)
    cleaned = drop_fully_duplicated_rows(cleaned, text_columns)
    removed_duplicate_rows = before_rows - len(cleaned)
    if removed_duplicate_rows:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=f"Removed {removed_duplicate_rows} fully duplicated row(s)",
            )
        )

    cleaned = cleaned.reset_index(drop=True)
    ordered_columns = [column for column in REQUIRED_COLUMNS if column in cleaned.columns]
    if SOURCE_ROW_COLUMN in cleaned.columns:
        ordered_columns.append(SOURCE_ROW_COLUMN)
    cleaned = cleaned[ordered_columns]
    return cleaned, report


def _sync_date_years_with_result_id(frame: pd.DataFrame) -> int:
    corrected_rows = 0
    for row_index, row in frame.iterrows():
        result_year = parse_result_id_year(str(row[RESULT_ID_COLUMN]).strip())
        if result_year is None:
            continue

        row_changed = False
        for date_column in DATE_COLUMNS:
            date_value = str(row[date_column]).strip()
            if not is_valid_micro_date(date_value):
                continue
            _day, _month, year_text = date_value.split(".")
            if int(year_text) == result_year:
                continue
            replacement = replace_micro_date_year(date_value, result_year)
            if replacement is None or replacement == date_value:
                continue
            frame.at[row_index, date_column] = replacement
            row_changed = True

        if row_changed:
            corrected_rows += 1
    return corrected_rows
