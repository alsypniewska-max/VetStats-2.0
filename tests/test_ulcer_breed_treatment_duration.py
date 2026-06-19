"""Tests for ulcer breed treatment duration analysis (section 1B)."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.chart_specs import build_ulcer_breed_treatment_duration_charts
from vetstats_app.analysis.ulcer_breed_treatment_duration import (
    MIN_DISPLAY_GROUP_SIZE,
    build_interpretation_summary,
    compute_ulcer_breed_treatment_duration,
)


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


def test_compute_ulcer_breed_treatment_duration_separates_species_and_ulcer_types() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1", type_of_ulcer="e"),
            _clinical_row(
                patient_ID="2",
                type_of_ulcer="s",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            ),
            _clinical_row(
                patient_ID="3",
                type_of_ulcer="e",
                date_appointment_first_before_micro="1.11.2024",
                date_last_appointment="25.03.2025",
            ),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="dog", breed="labrador"),
            _patient_row(patient_ID="2", species="cat", breed="persian"),
            _patient_row(patient_ID="3", species="dog", breed="beagle"),
        ]
    )

    result = compute_ulcer_breed_treatment_duration(clinical, patient)

    assert result.is_success
    assert result.exclusions.included_healed_with_duration == 3
    assert len(result.dog_ulcer_types) == 1
    assert result.dog_ulcer_types[0].ulcer_code == "e"
    assert result.dog_ulcer_types[0].count == 2
    assert len(result.cat_ulcer_types) == 1
    assert result.cat_ulcer_types[0].ulcer_code == "s"


def test_unknown_species_and_breed_are_counted() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1"),
            _clinical_row(patient_ID="2"),
            _clinical_row(patient_ID="3", type_of_ulcer="xxx"),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="xxx", breed="labrador"),
            _patient_row(patient_ID="2", species="dog", breed="xxx"),
            _patient_row(patient_ID="3", species="dog", breed="beagle"),
        ]
    )

    result = compute_ulcer_breed_treatment_duration(clinical, patient)

    assert result.exclusions.excluded_unknown_species == 1
    assert result.exclusions.excluded_unknown_breed == 1
    assert result.exclusions.excluded_non_ulcer == 1
    assert result.exclusions.included_with_known_breed == 0


def test_breed_ulcer_groups_below_min_n_are_excluded_from_tables() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE - 1):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, type_of_ulcer="e"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )

    result = compute_ulcer_breed_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )

    assert result.exclusions.excluded_below_min_n == MIN_DISPLAY_GROUP_SIZE - 1
    assert result.exclusions.included_in_breed_ulcer_tables == 0
    assert len(result.dog_breed_ulcer_rows) == 0


def test_breed_ulcer_groups_at_min_n_are_included() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, type_of_ulcer="e"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )

    result = compute_ulcer_breed_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )

    assert result.exclusions.excluded_below_min_n == 0
    assert result.exclusions.included_in_breed_ulcer_tables == MIN_DISPLAY_GROUP_SIZE
    assert len(result.dog_breed_ulcer_rows) == 1
    assert result.dog_breed_ulcer_rows[0].count == MIN_DISPLAY_GROUP_SIZE


def test_ulcer_type_summaries_include_unknown_breed_cases() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1", type_of_ulcer="e"),
            _clinical_row(patient_ID="2", type_of_ulcer="e"),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="dog", breed="labrador"),
            _patient_row(patient_ID="2", species="dog", breed="xxx"),
        ]
    )

    result = compute_ulcer_breed_treatment_duration(clinical, patient)

    assert len(result.dog_ulcer_types) == 1
    assert result.dog_ulcer_types[0].count == 2
    assert result.exclusions.excluded_unknown_breed == 1
    assert len(result.dog_breed_ulcer_rows) == 0
    assert result.exclusions.excluded_below_min_n == 1


def test_interpretation_mentions_terminal_ulcer_code_and_min_n_rule() -> None:
    clinical = pd.DataFrame([_clinical_row()])
    patient = pd.DataFrame([_patient_row()])

    result = compute_ulcer_breed_treatment_duration(clinical, patient)
    interpretation = build_interpretation_summary(result).lower()

    assert "terminal_ulcer_code" in interpretation
    assert f"n≥{MIN_DISPLAY_GROUP_SIZE}" in interpretation or "n>=" in interpretation


def test_terminal_ulcer_code_used_from_terminal_row() -> None:
    clinical = pd.DataFrame(
        [
            {
                "patient_ID": "1",
                "eye": "l",
                "type_of_ulcer": "e",
                "date_appointment_first_before_micro": "1.09.2024",
                "date_last_appointment": "10.09.2024",
                "how_ended": "continuation",
            },
            {
                "patient_ID": "1",
                "eye": "l",
                "type_of_ulcer": "s",
                "date_appointment_first_before_micro": "1.09.2024",
                "date_last_appointment": "15.01.2025",
                "how_ended": "good",
            },
        ]
    )
    patient = pd.DataFrame(
        [_patient_row(patient_ID="1", species="dog", breed="labrador")]
    )

    result = compute_ulcer_breed_treatment_duration(clinical, patient)

    assert result.exclusions.included_healed_with_duration == 1
    assert len(result.dog_ulcer_types) == 1
    assert result.dog_ulcer_types[0].ulcer_code == "s"
    assert result.dog_ulcer_types[0].ulcer_code != "e"


def test_ulcer_breed_treatment_duration_charts_generated() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, type_of_ulcer="e"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )
    clinical_rows.append(
        _clinical_row(
            patient_ID="99",
            type_of_ulcer="s",
            date_appointment_first_before_micro="1.10.2024",
            date_last_appointment="20.02.2025",
        )
    )
    patient_rows.append(
        _patient_row(patient_ID="99", species="cat", breed="persian")
    )

    result = compute_ulcer_breed_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    charts = build_ulcer_breed_treatment_duration_charts(result)

    chart_ids = {chart.chart_id for chart in charts}
    assert "ulcer_breed_dog_ulcer_types_box" in chart_ids
    assert "ulcer_breed_dog_top_breed_ulcer_box" in chart_ids


def test_chart_builder_caps_top_breed_ulcer_groups() -> None:
    from vetstats_app.analysis.ulcer_breed_treatment_duration import TOP_BREED_ULCER_CHART_LIMIT

    clinical_rows = []
    patient_rows = []
    for breed_index in range(TOP_BREED_ULCER_CHART_LIMIT + 3):
        for case_index in range(MIN_DISPLAY_GROUP_SIZE):
            patient_id = f"{breed_index}-{case_index}"
            clinical_rows.append(
                _clinical_row(patient_ID=patient_id, type_of_ulcer="e")
            )
            patient_rows.append(
                _patient_row(
                    patient_ID=patient_id,
                    species="dog",
                    breed=f"breed_{breed_index}",
                )
            )

    result = compute_ulcer_breed_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    charts = build_ulcer_breed_treatment_duration_charts(result)
    top_box = next(
        chart
        for chart in charts
        if chart.chart_id == "ulcer_breed_dog_top_breed_ulcer_box"
    )

    assert len(result.dog_breed_ulcer_rows) > TOP_BREED_ULCER_CHART_LIMIT
    assert len(top_box.labels) == TOP_BREED_ULCER_CHART_LIMIT


def test_report_payload_and_pdf_export() -> None:
    from pathlib import Path
    import tempfile

    from vetstats_app.services.analysis_report_service import AnalysisReportService

    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, type_of_ulcer="e"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )

    result = compute_ulcer_breed_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    service = AnalysisReportService()

    payload = service.build_ulcer_breed_treatment_duration_payload(result)
    assert payload.section_title == "Typ wrzodu a czas leczenia w obrębie ras"
    assert payload.table_blocks
    assert payload.chart_specs

    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir) / "ulcer_breed_treatment_duration_report.pdf"
        error = service.export_ulcer_breed_treatment_duration_report_pdf(
            result,
            destination,
        )
        assert error is None
        assert destination.is_file()
        assert destination.stat().st_size > 1000
