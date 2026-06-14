"""Cross-file referential integrity validation."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.schemas.patient import PATIENT_ID_COLUMN
from data_sterilizer.validation.issues import Issue, Severity, ValidationReport

CROSS_FILE_DATASET = "cross_file"


def validate_cross_file(datasets: dict[str, pd.DataFrame]) -> ValidationReport:
    """Verify patient_ID references in clinical and micro exist in patient."""
    report = ValidationReport()

    if "patient" not in datasets:
        return report

    known_patient_ids = _patient_ids(datasets["patient"])

    if "clinical" in datasets:
        report.extend(
            _validate_patient_references(
                datasets["clinical"],
                source_dataset="clinical",
                known_patient_ids=known_patient_ids,
            )
        )

    if "micro" in datasets:
        report.extend(
            _validate_patient_references(
                datasets["micro"],
                source_dataset="micro",
                known_patient_ids=known_patient_ids,
            )
        )

    return report


def _patient_ids(patient_frame: pd.DataFrame) -> set[str]:
    if PATIENT_ID_COLUMN not in patient_frame.columns:
        return set()

    return {
        str(value).strip()
        for value in patient_frame[PATIENT_ID_COLUMN].tolist()
        if str(value).strip()
    }


def _validate_patient_references(
    frame: pd.DataFrame,
    *,
    source_dataset: str,
    known_patient_ids: set[str],
) -> ValidationReport:
    report = ValidationReport()

    if PATIENT_ID_COLUMN not in frame.columns:
        return report

    for row_index, row in frame.iterrows():
        patient_id = str(row[PATIENT_ID_COLUMN]).strip()
        if patient_id == "" or patient_id in known_patient_ids:
            continue

        source_row = int(row[SOURCE_ROW_COLUMN]) if SOURCE_ROW_COLUMN in frame.columns else None
        report.add(
            Issue(
                severity=Severity.ERROR,
                dataset=CROSS_FILE_DATASET,
                row=source_row,
                column=PATIENT_ID_COLUMN,
                message=(
                    f"patient_ID {patient_id} referenced in {source_dataset}.csv "
                    f"does not exist in patient.csv"
                ),
            )
        )

    return report
