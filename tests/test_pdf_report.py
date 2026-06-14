"""Tests for PDF report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_sterilizer.cleaning.report import CleaningReport, Correction
from data_sterilizer.config import SterilizerPaths
from data_sterilizer.reporting.pdf_report import default_report_path, write_pdf_report
from data_sterilizer.validation.issues import Issue, Severity, ValidationReport


@pytest.fixture
def sample_report_context(tmp_path: Path) -> dict:
    paths = SterilizerPaths(
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        reports_dir=tmp_path / "reports",
    )
    loaded = {
        "patient": pd.DataFrame({"patient_ID": ["1"], "_source_row": [2]}),
        "clinical": pd.DataFrame({"patient_ID": ["1"], "_source_row": [2]}),
        "micro": pd.DataFrame({"patient_ID": ["1"], "_source_row": [2]}),
    }
    report = ValidationReport()
    report.add(
        Issue(
            severity=Severity.WARNING,
            dataset="patient",
            row=2,
            column="name",
            message="Example warning for scaffold test",
        )
    )
    cleaning_report = CleaningReport()
    cleaning_report.add(
        Correction(
            dataset="patient",
            message="Dropped trailing empty column(s): Unnamed: 8",
        )
    )
    return {
        "paths": paths,
        "loaded": loaded,
        "cleaned": {name: frame.copy() for name, frame in loaded.items()},
        "report": report,
        "cleaning_report": cleaning_report,
    }


def test_default_report_path_ends_with_pdf(tmp_path: Path) -> None:
    report_path = default_report_path(tmp_path / "reports")

    assert report_path.suffix == ".pdf"
    assert report_path.parent.name == "reports"


def test_write_pdf_report_creates_valid_pdf(sample_report_context: dict, tmp_path: Path) -> None:
    report_path = tmp_path / "reports" / "test_report.pdf"

    result_path = write_pdf_report(
        report_path,
        paths=sample_report_context["paths"],
        validation_report=sample_report_context["report"],
        cleaning_report=sample_report_context["cleaning_report"],
        loaded_datasets=sample_report_context["loaded"],
        cleaned_datasets=sample_report_context["cleaned"],
        dry_run=True,
        output_files={},
    )

    assert result_path == report_path
    assert report_path.is_file()
    assert report_path.read_bytes()[:4] == b"%PDF"


def test_write_pdf_report_rejects_non_pdf_suffix(tmp_path: Path, sample_report_context: dict) -> None:
    with pytest.raises(ValueError, match="\.pdf"):
        write_pdf_report(
            tmp_path / "report.txt",
            paths=sample_report_context["paths"],
            validation_report=sample_report_context["report"],
            cleaning_report=sample_report_context["cleaning_report"],
            loaded_datasets=sample_report_context["loaded"],
            cleaned_datasets=sample_report_context["cleaned"],
            dry_run=False,
            output_files={},
        )
