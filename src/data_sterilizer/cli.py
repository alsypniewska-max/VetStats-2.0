"""Command-line interface for the Data Sterilizer."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from data_sterilizer.config import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPORTS_DIR,
    SterilizerPaths,
)
from data_sterilizer.io.loader import LoadError
from data_sterilizer.io.writer import WriteError
from data_sterilizer.pipeline import run
from data_sterilizer.reporting.pdf_report import PdfReportError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data_sterilizer",
        description="Validate and clean veterinary patient CSV data.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing patient.csv, clinical.csv, and micro.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for cleaned CSV output",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="PDF report output path (must end with .pdf)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report only; do not write cleaned CSV files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if ERROR-level validation issues remain",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.report is not None and args.report.suffix.lower() != ".pdf":
        parser.error("--report must be a .pdf file path")

    paths = SterilizerPaths(
        input_dir=args.input,
        output_dir=args.output,
        reports_dir=args.report.parent if args.report is not None else DEFAULT_REPORTS_DIR,
    )

    try:
        result = run(paths, dry_run=args.dry_run, report_path=args.report)
    except (LoadError, WriteError, PdfReportError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"PDF report written to: {result.report_path}")

    if args.strict and not result.success:
        return 1

    return 0
