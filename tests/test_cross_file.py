"""Tests for cross-file referential integrity validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_sterilizer.io.loader import SOURCE_ROW_COLUMN
from data_sterilizer.reporting.pdf_report import write_pdf_report
from data_sterilizer.validation.cross_file import CROSS_FILE_DATASET, validate_cross_file
from data_sterilizer.validation.runner import validate_all


def _patient_row(patient_id: str = "1") -> dict[str, str]:
    return {
        "patient_ID": patient_id,
        "name": "latte",
        "date_of_birth": "4.01.2016",
        "species": "dog",
        "breed": "shih tzu",
        "gender": "m",
        "diseases_not_opht": "x",
        "other_diseases_opht": "x",
        SOURCE_ROW_COLUMN: "2",
    }


def _clinical_row(patient_id: str = "1") -> dict[str, str]:
    return {
        "patient_ID": patient_id,
        "eye": "l",
        "type_of_ulcer": "s",
        "date_appointment_first_before_micro": "3.01.2025",
        "duration_of_problem": "2 weeks",
        "drug_used_before_micro": "tobrex",
        "farmacology_surgery": "f",
        "topical_systemic": "t",
        "EMS": "yes",
        "type_of_surgery": "x",
        "top_treatment_after": "x",
        "sys_treatment_after": "x",
        "how_ended": "good",
        SOURCE_ROW_COLUMN: "2",
    }


def _micro_row(patient_id: str = "1") -> dict[str, str]:
    return {
        "patient_ID": patient_id,
        "result_ID": "003/2025",
        "date_result": "10.01.2025",
        "date_received": "7.01.2025",
        "date_collect": "3.01.2025",
        "bacteria": "negative",
        "growth": "x",
        "amikacin": "x",
        "amoxy/clavulanic": "x",
        "azithromycin": "x",
        "Cephalexin": "x",
        "Ceftriaxon": "x",
        "Ciprofloxacin": "x",
        "Chloramfenicol": "x",
        "Doxycycline": "x",
        "Enrofloxacin": "x",
        "Erythromycin": "x",
        "Gentamycin": "x",
        "Marbofloxacin": "x",
        "Moxifloxacin": "x",
        "Neomycin": "x",
        "Ofloxacin": "x",
        "Tobramycin": "x",
        SOURCE_ROW_COLUMN: "2",
    }


def test_validate_cross_file_passes_when_references_exist() -> None:
    datasets = {
        "patient": pd.DataFrame([_patient_row("1")]),
        "clinical": pd.DataFrame([_clinical_row("1")]),
        "micro": pd.DataFrame([_micro_row("1")]),
    }

    report = validate_cross_file(datasets)

    assert report.error_count == 0


def test_validate_cross_file_detects_missing_clinical_patient_reference() -> None:
    datasets = {
        "patient": pd.DataFrame([_patient_row("1")]),
        "clinical": pd.DataFrame([_clinical_row("99")]),
    }

    report = validate_cross_file(datasets)

    assert report.error_count == 1
    issue = report.issues[0]
    assert issue.dataset == CROSS_FILE_DATASET
    assert "clinical.csv" in issue.message
    assert "patient_ID 99" in issue.message


def test_validate_cross_file_detects_missing_micro_patient_reference() -> None:
    datasets = {
        "patient": pd.DataFrame([_patient_row("1")]),
        "micro": pd.DataFrame([_micro_row("77")]),
    }

    report = validate_cross_file(datasets)

    assert report.error_count == 1
    assert "micro.csv" in report.issues[0].message
    assert "patient_ID 77" in report.issues[0].message


def test_validate_all_runs_cross_file_only_when_enabled() -> None:
    datasets = {
        "patient": pd.DataFrame([_patient_row("1")]),
        "clinical": pd.DataFrame([_clinical_row("99")]),
    }

    without_cross_file = validate_all(datasets, cross_file=False)
    with_cross_file = validate_all(datasets, cross_file=True)

    assert len(without_cross_file.cross_file_issues) == 0
    assert len(with_cross_file.cross_file_issues) == 1


def test_pdf_report_includes_cross_file_section(tmp_path: Path) -> None:
    from data_sterilizer.cleaning.report import CleaningReport
    from data_sterilizer.config import SterilizerPaths

    validation_report = validate_cross_file(
        {
            "patient": pd.DataFrame([_patient_row("1")]),
            "clinical": pd.DataFrame([_clinical_row("99")]),
        }
    )
    paths = SterilizerPaths(
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        reports_dir=tmp_path / "reports",
    )
    loaded = {
        "patient": pd.DataFrame([_patient_row("1")]),
        "clinical": pd.DataFrame([_clinical_row("99")]),
    }
    report_path = tmp_path / "cross_file.pdf"

    write_pdf_report(
        report_path,
        paths=paths,
        validation_report=validation_report,
        cleaning_report=CleaningReport(),
        loaded_datasets=loaded,
        cleaned_datasets=loaded,
        dry_run=True,
        output_files={},
    )

    assert len(validation_report.cross_file_issues) == 1
    assert report_path.is_file()
    assert report_path.read_bytes()[:4] == b"%PDF"
