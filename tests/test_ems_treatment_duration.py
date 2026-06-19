"""Tests for EMS treatment duration analysis (section 2)."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.chart_specs import build_ems_treatment_duration_charts
from vetstats_app.analysis.ems_treatment_duration import (
    MIN_DISPLAY_GROUP_SIZE,
    MIN_TEST_GROUP_SIZE,
    build_interpretation_summary,
    compute_ems_treatment_duration,
    dog_overall_comparison_table_block,
    overall_comparison_table_block,
)


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "eye": "l",
        "type_of_ulcer": "e",
        "date_appointment_first_before_micro": "1.09.2024",
        "date_last_appointment": "15.01.2025",
        "how_ended": "good",
        "farmacology_surgery": "f",
        "EMS": "yes",
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


def test_compute_ems_treatment_duration_filters_pharmacology_and_ems() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1", EMS="yes"),
            _clinical_row(
                patient_ID="2",
                EMS="no",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            ),
            _clinical_row(patient_ID="3", farmacology_surgery="s"),
            _clinical_row(patient_ID="4", EMS="xxx"),
            _clinical_row(patient_ID="5", type_of_ulcer="xxx"),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1"),
            _patient_row(patient_ID="2", species="cat", breed="persian"),
            _patient_row(patient_ID="3"),
            _patient_row(patient_ID="4"),
            _patient_row(patient_ID="5"),
        ]
    )

    result = compute_ems_treatment_duration(clinical, patient)

    assert result.is_success
    assert result.exclusions.included_pharmacological_ems_cases == 2
    assert result.exclusions.included_ems_yes == 1
    assert result.exclusions.included_ems_no == 1
    assert result.exclusions.excluded_non_pharmacological == 1
    assert result.exclusions.excluded_invalid_ems == 1
    assert result.exclusions.excluded_non_ulcer == 1


def test_ems_values_read_from_terminal_row() -> None:
    clinical = pd.DataFrame(
        [
            {
                "patient_ID": "1",
                "eye": "l",
                "type_of_ulcer": "e",
                "date_appointment_first_before_micro": "1.09.2024",
                "date_last_appointment": "10.09.2024",
                "how_ended": "continuation",
                "farmacology_surgery": "f",
                "EMS": "no",
            },
            {
                "patient_ID": "1",
                "eye": "l",
                "type_of_ulcer": "s",
                "date_appointment_first_before_micro": "1.09.2024",
                "date_last_appointment": "15.01.2025",
                "how_ended": "good",
                "farmacology_surgery": "f",
                "EMS": "yes",
            },
        ]
    )
    patient = pd.DataFrame([_patient_row()])

    result = compute_ems_treatment_duration(clinical, patient)

    assert result.exclusions.included_pharmacological_ems_cases == 1
    assert result.exclusions.included_ems_yes == 1
    assert result.exclusions.included_ems_no == 0


def test_terminal_ulcer_code_used_from_terminal_row() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes", type_of_ulcer="s"))
        patient_rows.append(_patient_row(patient_ID=patient_id))
    clinical_rows.extend(
        [
            {
                "patient_ID": "99",
                "eye": "l",
                "type_of_ulcer": "e",
                "date_appointment_first_before_micro": "1.09.2024",
                "date_last_appointment": "10.09.2024",
                "how_ended": "continuation",
                "farmacology_surgery": "f",
                "EMS": "no",
            },
            {
                "patient_ID": "99",
                "eye": "l",
                "type_of_ulcer": "s",
                "date_appointment_first_before_micro": "1.09.2024",
                "date_last_appointment": "15.01.2025",
                "how_ended": "good",
                "farmacology_surgery": "f",
                "EMS": "yes",
            },
        ]
    )
    patient_rows.append(_patient_row(patient_ID="99"))

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    ulcer_codes = {row.ulcer_code for row in result.ulcer_comparisons}

    assert result.exclusions.included_pharmacological_ems_cases == MIN_DISPLAY_GROUP_SIZE + 1
    assert ulcer_codes == {"s"}
    assert "e" not in ulcer_codes


def test_species_layers_are_separate() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(patient_ID="1", EMS="yes"),
            _clinical_row(
                patient_ID="2",
                EMS="no",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            ),
        ]
    )
    patient = pd.DataFrame(
        [
            _patient_row(patient_ID="1", species="dog", breed="labrador"),
            _patient_row(patient_ID="2", species="cat", breed="persian"),
        ]
    )

    result = compute_ems_treatment_duration(clinical, patient)

    assert result.dog_overall_comparison is not None
    assert result.cat_overall_comparison is not None
    assert result.dog_overall_comparison.context_label == "Psy"
    assert result.cat_overall_comparison.context_label == "Koty"


def test_mann_whitney_unavailable_for_small_ems_arms() -> None:
    clinical = pd.DataFrame([_clinical_row(patient_ID="1")])
    patient = pd.DataFrame([_patient_row()])

    result = compute_ems_treatment_duration(clinical, patient)
    overall_test = result.statistical_tests[0]

    assert overall_test.note == "test niedostępny (za mała liczba przypadków)"


def test_mann_whitney_runs_with_sufficient_ems_arms() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed=f"breed_{index}")
        )
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 6)
        clinical_rows.append(
            _clinical_row(
                patient_ID=patient_id,
                EMS="no",
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

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    overall_test = result.statistical_tests[0]

    assert overall_test.note == ""
    assert overall_test.raw_p_value != "—"
    assert overall_test.median_difference_days != "—"


def test_bh_correction_applied_to_ulcer_type_tests() -> None:
    clinical_rows = []
    patient_rows = []
    ulcer_codes = ("e", "s")
    for ulcer_index, ulcer_code in enumerate(ulcer_codes):
        for ems in ("yes", "no"):
            for index in range(MIN_TEST_GROUP_SIZE):
                patient_id = f"{ulcer_code}-{ems}-{index}"
                clinical_rows.append(
                    _clinical_row(
                        patient_ID=patient_id,
                        type_of_ulcer=ulcer_code,
                        EMS=ems,
                        date_appointment_first_before_micro="1.09.2024",
                        date_last_appointment="15.01.2025",
                    )
                )
                patient_rows.append(
                    _patient_row(
                        patient_ID=patient_id,
                        species="dog",
                        breed=f"breed_{ulcer_index}_{index}",
                    )
                )

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    ulcer_tests = [
        test
        for test in result.statistical_tests
        if test.comparison_label.startswith("Łącznie —")
        and ":" in test.comparison_label
    ]

    assert len(ulcer_tests) == 2
    assert all(test.corrected_p_value != "—" for test in ulcer_tests)


def test_dog_breed_layer_hidden_when_below_display_threshold() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE - 1):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )

    assert len(result.dog_breed_comparisons) == 0


def test_dog_breed_shown_when_one_ems_arm_meets_display_threshold() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )
    clinical_rows.append(_clinical_row(patient_ID="99", EMS="no"))
    patient_rows.append(_patient_row(patient_ID="99", species="dog", breed="labrador"))

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )

    assert len(result.dog_breed_comparisons) == 1
    breed_row = result.dog_breed_comparisons[0]
    assert breed_row.breed_label == "labrador"
    assert breed_row.ems_yes is not None
    assert breed_row.ems_no is None
    chart_ids = {
        chart.chart_id
        for chart in build_ems_treatment_duration_charts(result)
    }
    assert "ems_treatment_dog_breed_grouped_bar" not in chart_ids


def test_overall_comparison_keeps_raw_p_value_without_bh() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(_patient_row(patient_ID=patient_id))
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 6)
        clinical_rows.append(
            _clinical_row(
                patient_ID=patient_id,
                EMS="no",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            )
        )
        patient_rows.append(_patient_row(patient_ID=patient_id))

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    overall_test = result.statistical_tests[0]

    assert overall_test.comparison_label == "Łącznie — EMS tak vs EMS nie"
    assert overall_test.raw_p_value != "—"
    assert overall_test.corrected_p_value == "—"


def test_unknown_species_included_in_pooled_excluded_from_dog_layer() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(
            _patient_row(patient_ID=patient_id, species="dog", breed="labrador")
        )
    for index in range(MIN_DISPLAY_GROUP_SIZE):
        patient_id = str(index + 10)
        clinical_rows.append(
            _clinical_row(
                patient_ID=patient_id,
                EMS="no",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            )
        )
        patient_rows.append(
            _patient_row(
                patient_ID=patient_id,
                species="unknown_species",
                breed="mystery",
            )
        )

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )

    assert result.exclusions.included_pharmacological_ems_cases == MIN_DISPLAY_GROUP_SIZE * 2
    assert result.exclusions.excluded_unknown_species == MIN_DISPLAY_GROUP_SIZE
    pooled_rows = overall_comparison_table_block(result).rows
    dog_rows = dog_overall_comparison_table_block(result).rows
    assert len(pooled_rows) == 2
    assert {row[1] for row in pooled_rows} == {"EMS tak", "EMS nie"}
    assert dog_rows
    assert {row[1] for row in dog_rows} == {"EMS tak"}
    interpretation = build_interpretation_summary(result).lower()
    assert "nieznanego gatunku" in interpretation
    assert "łącznym" in interpretation


def test_ems_treatment_duration_charts_generated() -> None:
    clinical_rows = []
    patient_rows = []
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(_patient_row(patient_ID=patient_id))
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 6)
        clinical_rows.append(
            _clinical_row(
                patient_ID=patient_id,
                EMS="no",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            )
        )
        patient_rows.append(_patient_row(patient_ID=patient_id, species="cat"))

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    charts = build_ems_treatment_duration_charts(result)
    chart_ids = {chart.chart_id for chart in charts}

    assert "ems_treatment_overall_box" in chart_ids
    assert "ems_treatment_dog_overall_box" in chart_ids
    assert "ems_treatment_cat_overall_box" in chart_ids


def test_interpretation_mentions_association_and_pharmacology_scope() -> None:
    clinical = pd.DataFrame([_clinical_row()])
    patient = pd.DataFrame([_patient_row()])
    result = compute_ems_treatment_duration(clinical, patient)
    interpretation = build_interpretation_summary(result).lower()

    assert "skojarzenie" in interpretation
    assert "farmakolog" in interpretation
    assert "ems" in interpretation


def test_report_payload_and_pdf_export() -> None:
    from pathlib import Path
    import tempfile

    from vetstats_app.services.analysis_report_service import AnalysisReportService

    clinical_rows = []
    patient_rows = []
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 1)
        clinical_rows.append(_clinical_row(patient_ID=patient_id, EMS="yes"))
        patient_rows.append(_patient_row(patient_ID=patient_id))
    for index in range(MIN_TEST_GROUP_SIZE):
        patient_id = str(index + 6)
        clinical_rows.append(
            _clinical_row(
                patient_ID=patient_id,
                EMS="no",
                date_appointment_first_before_micro="1.10.2024",
                date_last_appointment="20.02.2025",
            )
        )
        patient_rows.append(_patient_row(patient_ID=patient_id))

    result = compute_ems_treatment_duration(
        pd.DataFrame(clinical_rows),
        pd.DataFrame(patient_rows),
    )
    service = AnalysisReportService()

    payload = service.build_ems_treatment_duration_payload(result)
    assert payload.section_title == "Stosowanie EMS a czas leczenia"
    assert payload.table_blocks
    assert payload.chart_specs

    with tempfile.TemporaryDirectory() as temp_dir:
        destination = Path(temp_dir) / "ems_treatment_duration_report.pdf"
        error = service.export_ems_treatment_duration_report_pdf(result, destination)
        assert error is None
        assert destination.is_file()
        assert destination.stat().st_size > 1000
