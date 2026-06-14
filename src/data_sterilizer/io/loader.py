"""Load raw CSV inputs for the Data Sterilizer pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_sterilizer.config import CSV_DELIMITER, INPUT_FILE_NAMES, SterilizerPaths

SOURCE_ROW_COLUMN = "_source_row"

DATASET_KEYS: dict[str, str] = {
    "patient.csv": "patient",
    "clinical.csv": "clinical",
    "micro.csv": "micro",
}


class LoadError(Exception):
    """Raised when one or more input files cannot be loaded."""


def load_csv(path: Path) -> pd.DataFrame:
    """Load a single semicolon-separated CSV file."""
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    frame = pd.read_csv(
        path,
        sep=CSV_DELIMITER,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )
    frame.columns = [str(column).strip().lstrip("\ufeff") for column in frame.columns]
    frame = _drop_blank_rows(frame)
    frame[SOURCE_ROW_COLUMN] = range(2, len(frame) + 2)
    return frame.reset_index(drop=True)


def load_all(paths: SterilizerPaths) -> dict[str, pd.DataFrame]:
    """Load all required input CSV files keyed by dataset name."""
    datasets: dict[str, pd.DataFrame] = {}
    errors: list[str] = []

    for file_name in INPUT_FILE_NAMES:
        file_path = paths.input_file(file_name)
        try:
            datasets[DATASET_KEYS[file_name]] = load_csv(file_path)
        except FileNotFoundError as exc:
            errors.append(str(exc))

    if errors:
        raise LoadError("\n".join(errors))

    return datasets


def _drop_blank_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where every cell is empty or whitespace."""
    if frame.empty:
        return frame

    non_empty = frame.apply(
        lambda row: any(str(value).strip() for value in row),
        axis=1,
    )
    return frame.loc[non_empty].copy()
