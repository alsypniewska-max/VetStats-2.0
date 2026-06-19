"""Tests for breed treatment duration analysis (section 1A)."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.breed_treatment_duration import (
    build_interpretation_summary,
    compute_breed_treatment_duration,
)
from vetstats_app.analysis.chart_specs import build_breed_treatment_duration_charts


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "eye": "l",
        "type_of_ulcer": "e",
        "date_appointment_first_before_micro": "1.09.2024",
        "date_last_appointment": "15.01.2025",
        "how_ended": "good",
    }
    row.update(overrides)
    return row


def _patient_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "species": "dog",
        "breed": "labrador",
        "date_of_birth": "1.01.2020",
    }
    row.update(overrides)
    return row


def test_compute_breed_treatment_duration_separates_species_and_breeds() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1"),
            _clinical_row(
                patient_ID="2",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            ),
            _clinical_row(
                patient_ID="3",
                type_of_ulcer="xxx",
                how_ended="good",
            ),
            _clinical_row(
                patient_ID="4",
                how_ended="enucleation",
            ),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="dog", breed="labrador"),
            _patient_row(patient_ID="2", species="cat", breed="persian"),
            _patient_row(patient_ID="3", species="dog", breed="beagle"),
            _patient_row(patient_ID="4", species="dog", breed="beagle"),
            _patient_row(patient_ID="5", species="xxx", breed="unknown"),
        ]
    )

    result = compute_breed_treatment_duration(clinical, patient)

    assert result.is_success
    assert result.exclusions.included_healed_with_duration == 2
    assert result.exclusions.excluded_non_ulcer == 1
    assert result.exclusions.excluded_enucleation == 1
    assert result.dog_summary is not None
    assert result.cat_summary is not None
    assert len(result.dog_breeds) == 1
    assert result.dog_breeds[0].group_label == "labrador"
    assert len(result.cat_breeds) == 1
    assert result.cat_breeds[0].group_label == "persian"


def test_unknown_species_and_breed_are_counted_in_exclusions() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1"),
            _clinical_row(patient_ID="2"),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="xxx", breed="labrador"),
            _patient_row(patient_ID="2", species="dog", breed="xxx"),
        ]
    )

    result = compute_breed_treatment_duration(clinical, patient)

    assert result.exclusions.excluded_unknown_species == 1
    assert result.exclusions.excluded_unknown_breed == 1
    assert result.exclusions.included_with_known_breed == 0


def test_statistical_tests_report_unavailable_for_small_samples() -> None:
    clinical = pd.DataFrame([_clinical_row(patient_ID="1")])
    patient = pd.DataFrame([_patient_row(patient_ID="1")])

    result = compute_breed_treatment_duration(clinical, patient)

    assert all(test.note for test in result.statistical_tests)


def test_breed_treatment_duration_charts_generated() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1"),
            _clinical_row(patient_ID="2"),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="dog", breed="labrador"),
            _patient_row(patient_ID="2", species="cat", breed="persian"),
        ]
    )

    result = compute_breed_treatment_duration(clinical, patient)
    charts = build_breed_treatment_duration_charts(result)

    assert any(chart.chart_id == "breed_treatment_species_box" for chart in charts)


def test_species_summary_can_exceed_breed_table_totals() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1"),
            _clinical_row(patient_ID="2"),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="dog", breed="labrador"),
            _patient_row(patient_ID="2", species="dog", breed="xxx"),
        ]
    )

    result = compute_breed_treatment_duration(clinical, patient)

    assert result.dog_summary is not None
    assert result.dog_summary.count == 2
    assert sum(row.count for row in result.dog_breeds) == 1
    assert result.exclusions.excluded_unknown_breed == 1
    interpretation = build_interpretation_summary(result).lower()
    assert "nieznanej rasy" in interpretation or "bez znanej rasy" in interpretation


def test_mann_whitney_runs_with_sufficient_samples() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(5):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed=f"breed_{index}")
        )
    for index in range(5):
        patient_id = str(index + 6)
        clinical_rows.append(
            _clinical_row(
                patient_ID=patient_id,
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            )
        )
        patient_rows.append(
            _patient_row(
                patient_ID=patient_id,
                species="cat",
                breed=f"cat_breed_{index}",
            )
        )

    result = compute_breed_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )

    species_test = result.statistical_tests[0]
    assert species_test.test_name == "Mann–Whitney U"
    assert not species_test.note
    assert species_test.p_value != "—"


def test_report_payload_and_pdf_export() -> None:
    from pathlib import Path
    import tempfile

    from vetstats_app.services.analysis_report_service import AnalysisReportService

    clinical = pd.DataFrame([_clinical_row()])
    patient = pd.DataFrame([_patient_row()])
    result = compute_breed_treatment_duration(clinical, patient)
    service = AnalysisReportService()

    payload = service.build_breed_treatment_duration_payload(result)
    assert payload.section_title == "Rasa a czas leczenia"
    assert payload.table_blocks
    assert payload.chart_specs

    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir) / "breed_treatment_duration_report.pdf"
        error = service.export_breed_treatment_duration_report_pdf(result, destination)
        assert error is None
        assert destination.is_file()
        assert destination.stat().st_size > 1000
