"""Cleaning rules for patient.csv."""

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
from data_sterilizer.schemas.patient import (
    DATASET_NAME,
    EMPTY_VALUE_REPLACEMENT,
    OTHER_DISEASES_OPHT_COLUMN,
    REQUIRED_COLUMNS,
    TEXT_COLUMNS,
    is_trailing_empty_column,
    normalize_column_names,
    normalize_other_diseases_opht_tokens,
)


def clean_patient(frame: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Apply patient-specific and global cleaning rules."""
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

    text_columns = [column for column in TEXT_COLUMNS if column in cleaned.columns]
    cleaned = trim_whitespace(cleaned, text_columns)
    cleaned = lowercase_text(cleaned, text_columns)

    if OTHER_DISEASES_OPHT_COLUMN in cleaned.columns:
        typo_corrections = 0
        for row_index, row in cleaned.iterrows():
            original = str(row[OTHER_DISEASES_OPHT_COLUMN]).strip().lower()
            normalized = normalize_other_diseases_opht_tokens(original)
            if normalized != original:
                cleaned.at[row_index, OTHER_DISEASES_OPHT_COLUMN] = normalized
                typo_corrections += 1
        if typo_corrections:
            report.add(
                Correction(
                    dataset=DATASET_NAME,
                    message=(
                        "Corrected other_diseases_opht token typos in "
                        f"{typo_corrections} row(s)"
                    ),
                )
            )

    cleaned = replace_empty_cells(cleaned, text_columns, EMPTY_VALUE_REPLACEMENT)

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
    ordered_columns = [column for column in REQUIRED_COLUMNS if column in cleaned.columns]
    if SOURCE_ROW_COLUMN in cleaned.columns:
        ordered_columns.append(SOURCE_ROW_COLUMN)
    cleaned = cleaned[ordered_columns]
    return cleaned, report
