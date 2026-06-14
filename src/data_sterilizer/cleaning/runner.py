"""Cleaning orchestration across datasets."""

from __future__ import annotations

import pandas as pd

from data_sterilizer.cleaning.clinical import clean_clinical
from data_sterilizer.cleaning.micro import clean_micro
from data_sterilizer.cleaning.patient import clean_patient
from data_sterilizer.cleaning.report import CleaningReport


def clean_all(datasets: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], CleaningReport]:
    """Run dataset cleaners and return cleaned data plus a correction report."""
    cleaned: dict[str, pd.DataFrame] = {}
    report = CleaningReport()

    for name, frame in datasets.items():
        if name == "patient":
            cleaned_frame, patient_report = clean_patient(frame)
            cleaned[name] = cleaned_frame
            report.extend(patient_report)
        elif name == "clinical":
            cleaned_frame, clinical_report = clean_clinical(frame)
            cleaned[name] = cleaned_frame
            report.extend(clinical_report)
        elif name == "micro":
            cleaned_frame, micro_report = clean_micro(frame)
            cleaned[name] = cleaned_frame
            report.extend(micro_report)
        else:
            cleaned[name] = frame.copy()

    return cleaned, report
