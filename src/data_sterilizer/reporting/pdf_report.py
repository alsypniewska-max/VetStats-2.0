"""Generate PDF validation reports for the Data Sterilizer pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from data_sterilizer.cleaning.report import CleaningReport
from data_sterilizer.config import SterilizerPaths
from data_sterilizer.validation.issues import Severity, ValidationReport


class PdfReportError(Exception):
    """Raised when a PDF report cannot be generated."""


def default_report_path(reports_dir: Path) -> Path:
    """Return an auto-generated PDF report path inside ``reports_dir``."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return reports_dir / f"sterilizer_report_{timestamp}.pdf"


def write_pdf_report(
    path: Path,
    *,
    paths: SterilizerPaths,
    validation_report: ValidationReport,
    cleaning_report: CleaningReport,
    loaded_datasets: dict[str, pd.DataFrame],
    cleaned_datasets: dict[str, pd.DataFrame],
    dry_run: bool,
    output_files: dict[str, Path],
) -> Path:
    """Write a PDF validation report and return the output path."""
    report_path = Path(path)
    if report_path.suffix.lower() != ".pdf":
        raise ValueError("Report path must end with .pdf")

    report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _build_pdf(
            report_path,
            paths=paths,
            validation_report=validation_report,
            cleaning_report=cleaning_report,
            loaded_datasets=loaded_datasets,
            cleaned_datasets=cleaned_datasets,
            dry_run=dry_run,
            output_files=output_files,
        )
    except OSError as exc:
        raise PdfReportError(f"Failed to write PDF report: {exc}") from exc

    return report_path


def _build_pdf(
    path: Path,
    *,
    paths: SterilizerPaths,
    validation_report: ValidationReport,
    cleaning_report: CleaningReport,
    loaded_datasets: dict[str, pd.DataFrame],
    cleaned_datasets: dict[str, pd.DataFrame],
    dry_run: bool,
    output_files: dict[str, Path],
) -> None:
    styles = getSampleStyleSheet()
    story: list = []

    story.append(Paragraph("VetStats 2.0 — Data Sterilizer Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", styles["Normal"]))
    story.append(Paragraph(f"Mode: {'dry-run' if dry_run else 'full run'}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Paths", styles["Heading2"]))
    story.append(Paragraph(f"Input: {paths.input_dir}", styles["Normal"]))
    story.append(Paragraph(f"Output: {paths.output_dir}", styles["Normal"]))
    story.append(Paragraph(f"Reports: {paths.reports_dir}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Dataset Summary", styles["Heading2"]))
    for dataset_name in sorted(loaded_datasets):
        loaded_count = len(loaded_datasets[dataset_name])
        cleaned_count = len(cleaned_datasets[dataset_name])
        story.append(
            Paragraph(
                f"{dataset_name}: loaded {loaded_count} rows, cleaned {cleaned_count} rows",
                styles["Normal"],
            )
        )
    story.append(Spacer(1, 12))

    story.append(Paragraph("Validation Summary", styles["Heading2"]))
    story.append(Paragraph(f"Errors: {validation_report.error_count}", styles["Normal"]))
    story.append(Paragraph(f"Warnings: {validation_report.warning_count}", styles["Normal"]))
    story.append(Paragraph(f"Total issues: {len(validation_report.issues)}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Cross-File Referential Integrity", styles["Heading2"]))
    if validation_report.cross_file_issues:
        for issue in validation_report.cross_file_issues:
            location = _format_issue_location(issue.dataset, issue.row, issue.column)
            story.append(
                Paragraph(
                    f"[{issue.severity.value}] {location}: {issue.message}",
                    styles["Normal"],
                )
            )
    else:
        story.append(Paragraph("No cross-file referential integrity issues reported.", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Table Issues", styles["Heading2"]))
    if validation_report.table_issues:
        for issue in validation_report.table_issues:
            location = _format_issue_location(issue.dataset, issue.row, issue.column)
            story.append(
                Paragraph(
                    f"[{issue.severity.value}] {location}: {issue.message}",
                    styles["Normal"],
                )
            )
    else:
        story.append(Paragraph("No table-specific issues reported.", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Corrections", styles["Heading2"]))
    if cleaning_report.corrections:
        for correction in cleaning_report.corrections:
            story.append(
                Paragraph(
                    f"[{correction.dataset}] {correction.message}",
                    styles["Normal"],
                )
            )
    else:
        story.append(Paragraph("No corrections applied.", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Output Files", styles["Heading2"]))
    if output_files:
        for dataset_name in sorted(output_files):
            story.append(Paragraph(f"{dataset_name}: {output_files[dataset_name]}", styles["Normal"]))
    elif dry_run:
        story.append(Paragraph("No CSV output written (dry-run).", styles["Normal"]))
    else:
        story.append(Paragraph("No CSV output files written.", styles["Normal"]))

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    doc.build(story)


def _format_issue_location(dataset: str, row: int | None, column: str | None) -> str:
    parts = [dataset]
    if row is not None:
        parts.append(f"row {row}")
    if column is not None:
        parts.append(f"column {column}")
    return " / ".join(parts)
