"""Tests for CSV loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from data_sterilizer.config import SterilizerPaths
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN, load_all, load_csv


def test_load_patient_csv_strips_bom_and_keeps_columns(sample_paths: SterilizerPaths) -> None:
    frame = load_csv(sample_paths.input_file("patient.csv"))

    assert "patient_ID" in frame.columns
    assert "﻿patient_ID" not in frame.columns
    assert len(frame) > 0


def test_load_micro_csv_drops_trailing_blank_rows(sample_paths: SterilizerPaths) -> None:
    frame = load_csv(sample_paths.input_file("micro.csv"))

    assert all(
        any(str(value).strip() for value in row)
        for _, row in frame.drop(columns=[SOURCE_ROW_COLUMN]).iterrows()
    )


def test_load_all_returns_three_datasets(sample_paths: SterilizerPaths) -> None:
    datasets = load_all(sample_paths)

    assert set(datasets) == {"patient", "clinical", "micro"}
    for frame in datasets.values():
        assert SOURCE_ROW_COLUMN in frame.columns


def test_load_csv_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_csv(tmp_path / "missing.csv")
