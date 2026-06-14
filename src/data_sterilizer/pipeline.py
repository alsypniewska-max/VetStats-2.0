"""Orchestrate load → validate → clean → re-validate → write → report."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from data_sterilizer.cleaning.report import CleaningReport
from data_sterilizer.cleaning.runner import clean_all
from data_sterilizer.config import SterilizerPaths
from data_sterilizer.io.loader import load_all
from data_sterilizer.io.writer import write_all
from data_sterilizer.reporting.pdf_report import default_report_path, write_pdf_report
from data_sterilizer.validation.issues import ValidationReport
from data_sterilizer.validation.runner import validate_all


@dataclass
class PipelineResult:
    """Summary of a single sterilizer pipeline run."""

    loaded_datasets: dict[str, pd.DataFrame] = field(default_factory=dict)
    cleaned_datasets: dict[str, pd.DataFrame] = field(default_factory=dict)
    validation_report: ValidationReport = field(default_factory=ValidationReport)
    cleaning_report: CleaningReport = field(default_factory=CleaningReport)
    output_files: dict[str, Path] = field(default_factory=dict)
    report_path: Path | None = None
    dry_run: bool = False

    @property
    def success(self) -> bool:
        return not self.validation_report.has_errors()


def run(
    paths: SterilizerPaths,
    *,
    dry_run: bool = False,
    report_path: Path | None = None,
) -> PipelineResult:
    """Execute the Data Sterilizer pipeline."""
    loaded = load_all(paths)

    validation_report = ValidationReport()
    validation_report.extend(validate_all(loaded, cross_file=False))

    cleaned, cleaning_report = clean_all(loaded)
    validation_report.extend(validate_all(cleaned, cross_file=True))

    output_files: dict[str, Path] = {}
    if not dry_run:
        output_files = write_all(cleaned, paths)

    resolved_report_path = report_path or default_report_path(paths.reports_dir)
    write_pdf_report(
        resolved_report_path,
        paths=paths,
        validation_report=validation_report,
        cleaning_report=cleaning_report,
        loaded_datasets=loaded,
        cleaned_datasets=cleaned,
        dry_run=dry_run,
        output_files=output_files,
    )

    return PipelineResult(
        loaded_datasets=loaded,
        cleaned_datasets=cleaned,
        validation_report=validation_report,
        cleaning_report=cleaning_report,
        output_files=output_files,
        report_path=resolved_report_path,
        dry_run=dry_run,
    )
