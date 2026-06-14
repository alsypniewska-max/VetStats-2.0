"""Tests for the pipeline skeleton."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_sterilizer.config import SterilizerPaths
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.pipeline import run


@pytest.fixture
def temp_paths(tmp_path: Path) -> SterilizerPaths:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    reports_dir = tmp_path / "reports"
    input_dir.mkdir()

    source_root = Path(__file__).resolve().parent.parent / "Data_to_check"
    for file_name in ("patient.csv", "clinical.csv", "micro.csv"):
        (input_dir / file_name).write_text(
            (source_root / file_name).read_text(encoding="utf-8-sig"),
            encoding="utf-8",
        )

    return SterilizerPaths(
        input_dir=input_dir,
        output_dir=output_dir,
        reports_dir=reports_dir,
    )


def test_pipeline_dry_run_writes_pdf_only(temp_paths: SterilizerPaths, tmp_path: Path) -> None:
    report_path = tmp_path / "pipeline_dry_run.pdf"
    result = run(temp_paths, dry_run=True, report_path=report_path)

    assert result.dry_run is True
    assert result.output_files == {}
    assert result.report_path == report_path
    assert report_path.is_file()
    assert report_path.read_bytes()[:4] == b"%PDF"
    assert set(result.loaded_datasets) == {"patient", "clinical", "micro"}
    assert not temp_paths.output_dir.exists() or not any(temp_paths.output_dir.iterdir())


def test_pipeline_writes_cleaned_csvs_and_pdf(temp_paths: SterilizerPaths, tmp_path: Path) -> None:
    report_path = tmp_path / "pipeline_full_run.pdf"
    result = run(temp_paths, dry_run=False, report_path=report_path)

    assert set(result.output_files) == {"patient", "clinical", "micro"}
    assert result.report_path == report_path
    assert report_path.is_file()
    assert any(
        "Dropped trailing empty column(s): Unnamed: 8" in correction.message
        for correction in result.cleaning_report.corrections
    )

    expected_output_names = {
        "patient": "patient_sterile.csv",
        "clinical": "clinical_sterile.csv",
        "micro": "micro_sterile.csv",
    }
    for dataset_key, output_path in result.output_files.items():
        assert output_path.name == expected_output_names[dataset_key]
        assert output_path.is_file()
        written = pd.read_csv(output_path, sep=";", dtype=str, keep_default_na=False)
        assert SOURCE_ROW_COLUMN not in written.columns
        assert len(written) == len(result.cleaned_datasets[dataset_key])


def test_pipeline_overwrites_existing_sterile_output(temp_paths: SterilizerPaths, tmp_path: Path) -> None:
    temp_paths.output_dir.mkdir(parents=True, exist_ok=True)
    stale_path = temp_paths.output_dir / "patient_sterile.csv"
    stale_path.write_text("stale content", encoding="utf-8")

    report_path = tmp_path / "pipeline_overwrite.pdf"
    result = run(temp_paths, dry_run=False, report_path=report_path)

    patient_output = result.output_files["patient"]
    assert patient_output == stale_path
    assert patient_output.read_text(encoding="utf-8") != "stale content"
    assert "patient_ID" in patient_output.read_text(encoding="utf-8")
