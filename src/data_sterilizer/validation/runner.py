"""Validation orchestration across datasets."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.validation.clinical import validate_clinical
from data_sterilizer.validation.cross_file import validate_cross_file
from data_sterilizer.validation.issues import ValidationReport
from data_sterilizer.validation.micro import validate_micro
from data_sterilizer.validation.patient import validate_patient


def validate_all(
    datasets: dict[str, pd.DataFrame],
    *,
    cross_file: bool = True,
) -> ValidationReport:
    """Run dataset validators and return a combined report."""
    report = ValidationReport()

    if "patient" in datasets:
        report.extend(validate_patient(datasets["patient"]))

    if "clinical" in datasets:
        report.extend(validate_clinical(datasets["clinical"]))

    if "micro" in datasets:
        report.extend(validate_micro(datasets["micro"]))

    if cross_file:
        report.extend(validate_cross_file(datasets))

    return report
