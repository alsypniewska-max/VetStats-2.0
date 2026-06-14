"""Write cleaned CSV outputs for the Data Sterilizer pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_sterilizer.config import (
    CSV_DELIMITER,
    CSV_ENCODING,
    INPUT_FILE_NAMES,
    SterilizerPaths,
    sterile_output_name,
)
from data_sterilizer.io.loader import DATASET_KEYS, SOURCE_ROW_COLUMN


class WriteError(Exception):
    """Raised when one or more output files cannot be written."""


def prepare_for_export(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy suitable for CSV export (internal columns removed)."""
    export_frame = frame.copy()
    if SOURCE_ROW_COLUMN in export_frame.columns:
        export_frame = export_frame.drop(columns=[SOURCE_ROW_COLUMN])
    return export_frame


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    """Write a single cleaned CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    export_frame = prepare_for_export(frame)
    export_frame.to_csv(
        path,
        sep=CSV_DELIMITER,
        encoding=CSV_ENCODING,
        index=False,
    )
    return path


def write_all(datasets: dict[str, pd.DataFrame], paths: SterilizerPaths) -> dict[str, Path]:
    """Write all cleaned datasets to the output directory."""
    output_files: dict[str, Path] = {}
    errors: list[str] = []

    for file_name in INPUT_FILE_NAMES:
        dataset_key = DATASET_KEYS[file_name]
        if dataset_key not in datasets:
            errors.append(f"Missing dataset for output file: {file_name}")
            continue

        output_path = paths.output_file(sterile_output_name(file_name))
        try:
            output_files[dataset_key] = write_csv(datasets[dataset_key], output_path)
        except OSError as exc:
            errors.append(f"Failed to write {output_path}: {exc}")

    if errors:
        raise WriteError("\n".join(errors))

    return output_files
