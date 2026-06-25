"""Cleaning rules for clinical.csv."""

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
from data_sterilizer.schemas.clinical import (
    CANONICAL_COLUMNS,
    DATASET_NAME,
    DATE_LAST_APPOINTMENT_COLUMN,
    DURATION_COLUMN,
    EMPTY_VALUE_REPLACEMENT,
    FARMACOLOGY_SURGERY_COLUMN,
    HOW_ENDED_COLUMN,
    HOW_ENDED_REQUIRES_X_DATE_LAST,
    NOT_APPLICABLE_VALUE,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    SYS_TREATMENT_COLUMN,
    TEXT_COLUMNS,
    TOP_TREATMENT_COLUMN,
    TYPE_OF_SURGERY_COLUMN,
    UNKNOWN_VALUE,
    is_trailing_empty_column,
    normalize_column_names,
    normalize_duration_value,
)


def clean_clinical(frame: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Apply clinical-specific and global cleaning rules."""
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

    text_columns = _text_columns_for_frame(cleaned)
    cleaned = trim_whitespace(cleaned, text_columns)
    cleaned = lowercase_text(cleaned, text_columns)

    farmacology_corrections = _apply_farmacology_surgery_corrections(cleaned)
    if farmacology_corrections:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=(
                    "Adjusted farmacology_surgery in "
                    f"{farmacology_corrections} row(s) based on surgery/treatment values"
                ),
            )
        )

    duration_corrections = _apply_duration_typo_corrections(cleaned)
    if duration_corrections:
        report.add(
            Correction(
                dataset=DATASET_NAME,
                message=(
                    "Corrected duration_of_problem unit typos in "
                    f"{duration_corrections} row(s)"
                ),
            )
        )

    if DATE_LAST_APPOINTMENT_COLUMN in cleaned.columns:
        date_last_corrections = _apply_date_last_appointment_corrections(cleaned)
        if date_last_corrections:
            report.add(
                Correction(
                    dataset=DATASET_NAME,
                    message=(
                        "Normalized date_last_appointment in "
                        f"{date_last_corrections} row(s)"
                    ),
                )
            )

    cleaned = replace_empty_cells(cleaned, text_columns, EMPTY_VALUE_REPLACEMENT)

    if HOW_ENDED_COLUMN in cleaned.columns:
        cleaned[HOW_ENDED_COLUMN] = cleaned[HOW_ENDED_COLUMN].map(
            lambda value: EMPTY_VALUE_REPLACEMENT
            if str(value).strip() == ""
            else str(value).strip()
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
    cleaned = cleaned[_ordered_output_columns(cleaned)]
    return cleaned, report


def _text_columns_for_frame(frame: pd.DataFrame) -> list[str]:
    columns = [column for column in TEXT_COLUMNS if column in frame.columns]
    for column in OPTIONAL_COLUMNS:
        if column in frame.columns and column not in columns:
            columns.append(column)
    return columns


def _ordered_output_columns(frame: pd.DataFrame) -> list[str]:
    ordered = [column for column in CANONICAL_COLUMNS if column in frame.columns]
    if SOURCE_ROW_COLUMN in frame.columns:
        ordered.append(SOURCE_ROW_COLUMN)
    return ordered


def _apply_farmacology_surgery_corrections(frame: pd.DataFrame) -> int:
    corrections = 0
    for row_index, row in frame.iterrows():
        surgery_value = str(row[TYPE_OF_SURGERY_COLUMN]).strip().lower()
        farmacology_value = str(row[FARMACOLOGY_SURGERY_COLUMN]).strip().lower()
        top_treatment = str(row[TOP_TREATMENT_COLUMN]).strip().lower()
        sys_treatment = str(row[SYS_TREATMENT_COLUMN]).strip().lower()
        updated = farmacology_value

        if surgery_value != NOT_APPLICABLE_VALUE and farmacology_value == "f":
            updated = "s"
        elif (
            surgery_value == NOT_APPLICABLE_VALUE
            and top_treatment == NOT_APPLICABLE_VALUE
            and sys_treatment == NOT_APPLICABLE_VALUE
            and farmacology_value != "f"
        ):
            updated = "f"

        if updated != farmacology_value:
            frame.at[row_index, FARMACOLOGY_SURGERY_COLUMN] = updated
            corrections += 1
    return corrections


def _apply_duration_typo_corrections(frame: pd.DataFrame) -> int:
    corrections = 0
    for row_index, row in frame.iterrows():
        original = str(row[DURATION_COLUMN]).strip().lower()
        normalized = normalize_duration_value(original)
        if normalized != original:
            frame.at[row_index, DURATION_COLUMN] = normalized
            corrections += 1
    return corrections


def _apply_date_last_appointment_corrections(frame: pd.DataFrame) -> int:
    corrections = 0
    for row_index, row in frame.iterrows():
        how_ended = str(row[HOW_ENDED_COLUMN]).strip().lower()
        date_last = str(row[DATE_LAST_APPOINTMENT_COLUMN]).strip().lower()
        updated = date_last

        if how_ended in HOW_ENDED_REQUIRES_X_DATE_LAST:
            updated = NOT_APPLICABLE_VALUE
        elif date_last == "":
            updated = UNKNOWN_VALUE

        if updated != date_last:
            frame.at[row_index, DATE_LAST_APPOINTMENT_COLUMN] = updated
            corrections += 1
    return corrections
