"""Tests for pre-swab drug analysis."""

from __future__ import annotations

import pandas as pd

from vetstats_app.analysis.chart_specs import build_pre_swab_drugs_charts
from vetstats_app.analysis.pre_swab_drugs import (
    NO_PRIOR_TREATMENT_LABEL,
    TREATED_BEFORE_SWAB_LABEL,
    UNKNOWN_DRUG_LABEL,
    build_interpretation_summary,
    classify_culture_outcome,
    classify_drug_field,
    compute_pre_swab_drugs,
    normalize_drug_token,
    split_drug_tokens_from_text,
    treatment_status_label_for_bucket,
)


def test_normalize_drug_token_trims_and_lowercases() -> None:
    assert normalize_drug_token("  TOBREX ") == "tobrex"


def test_split_drug_tokens_deduplicates_trivial_differences() -> None:
    assert split_drug_tokens_from_text("tobrex; TOBREX ;maxitrol") == ("tobrex", "maxitrol")


def test_classify_drug_field_separates_no_treatment_unknown_and_drugs() -> None:
    assert classify_drug_field("x") == ("no_prior_treatment", ())
    assert classify_drug_field("xxx") == ("unknown", ())
    assert classify_drug_field("tobrex") == ("drugs", ("tobrex",))


def test_classify_culture_outcome_detects_negative_single_and_mixed() -> None:
    assert classify_culture_outcome(("negative",)) == "Wynik negatywny"
    assert classify_culture_outcome(("streptococcus gr g",)) == "Pojedynczy wzrost bakteryjny"
    assert classify_culture_outcome(("streptococcus gr g", "staphylococcus")) == "Wzrost mieszany"


def _clinical_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "eye": "l",
        "type_of_ulcer": "e",
        "date_appointment_first_before_micro": "3.01.2025",
        "duration_of_problem": "2 weeks",
        "drug_used_before_micro": "tobrex",
        "farmacology_surgery": "f",
        "topical_systemic": "t",
        "EMS": "no",
        "type_of_surgery": "x",
        "top_treatment_after": "x",
        "sys_treatment_after": "x",
        "how_ended": "good",
    }
    row.update(overrides)
    return row


def _micro_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_ID": "1",
        "result_ID": "001/TEST",
        "date_collect": "5.01.2025",
        "date_result": "6.01.2025",
        "date_received": "4.01.2025",
        "bacteria": "negative",
        "growth": "none",
        "amikacin": "xxx",
    }
    row.update(overrides)
    return row


def test_compute_pre_swab_drugs_builds_counts_and_crosstab() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(drug_used_before_micro="x"),
            _clinical_row(patient_ID="2", drug_used_before_micro="xxx"),
            _clinical_row(patient_ID="3", drug_used_before_micro="tobrex;maxitrol"),
        ]
    )
    micro = pd.DataFrame(
        [
            _micro_row(patient_ID="1", bacteria="negative"),
            _micro_row(patient_ID="2", result_ID="002/TEST", bacteria="negative"),
            _micro_row(patient_ID="3", result_ID="003/TEST", bacteria="streptococcus gr g"),
            _micro_row(
                patient_ID="3",
                result_ID="003/TEST",
                bacteria="staphylococcus",
            ),
        ]
    )

    result = compute_pre_swab_drugs(clinical, micro)

    assert result.is_success
    assert result.no_prior_treatment_count == 1
    assert result.unknown_drug_count == 1
    assert result.with_known_drugs_count == 1
    assert result.top_drugs[0].drug_label == "tobrex"
    assert any(row.drug_label == NO_PRIOR_TREATMENT_LABEL for row in result.drug_culture_crosstab)
    assert any(row.drug_label == UNKNOWN_DRUG_LABEL for row in result.drug_culture_crosstab)
    assert any(row.culture_outcome == "Wzrost mieszany" for row in result.drug_culture_crosstab)


def test_treatment_status_label_for_bucket_uses_section_terminology() -> None:
    assert treatment_status_label_for_bucket("drugs") == TREATED_BEFORE_SWAB_LABEL
    assert treatment_status_label_for_bucket("no_prior_treatment") == NO_PRIOR_TREATMENT_LABEL
    assert treatment_status_label_for_bucket("unknown") == UNKNOWN_DRUG_LABEL


def test_treatment_status_culture_crosstab_counts_one_row_per_matched_case() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(drug_used_before_micro="x"),
            _clinical_row(patient_ID="2", drug_used_before_micro="xxx"),
            _clinical_row(patient_ID="3", drug_used_before_micro="tobrex;maxitrol"),
        ]
    )
    micro = pd.DataFrame(
        [
            _micro_row(patient_ID="1", bacteria="negative"),
            _micro_row(patient_ID="2", result_ID="002/TEST", bacteria="negative"),
            _micro_row(patient_ID="3", result_ID="003/TEST", bacteria="streptococcus gr g"),
            _micro_row(
                patient_ID="3",
                result_ID="003/TEST",
                bacteria="staphylococcus",
            ),
        ]
    )

    result = compute_pre_swab_drugs(clinical, micro)

    assert result.treatment_status_culture_crosstab
    status_counts = {
        row.treatment_status_label: row.count
        for row in result.treatment_status_culture_crosstab
        if row.culture_outcome == "Wzrost mieszany"
    }
    assert status_counts.get(TREATED_BEFORE_SWAB_LABEL) == 1
    assert sum(row.count for row in result.treatment_status_culture_crosstab) == 3


def test_pre_swab_drugs_charts_generated_for_valid_data() -> None:
    clinical = pd.DataFrame([_clinical_row(), _clinical_row(patient_ID="2", drug_used_before_micro="x")])
    micro = pd.DataFrame(
        [
            _micro_row(),
            _micro_row(patient_ID="2", result_ID="002/TEST"),
        ]
    )

    result = compute_pre_swab_drugs(clinical, micro)
    charts = build_pre_swab_drugs_charts(result)

    assert len(charts) >= 3
    assert any(chart.chart_id == "pre_swab_top_drugs" for chart in charts)
    assert any(chart.chart_id == "pre_swab_treatment_status_culture" for chart in charts)


def test_interpretation_summary_covers_section_charts() -> None:
    clinical = pd.DataFrame(
        [
            _clinical_row(drug_used_before_micro="x"),
            _clinical_row(patient_ID="2", drug_used_before_micro="xxx"),
            _clinical_row(patient_ID="3", drug_used_before_micro="tobrex;maxitrol"),
        ]
    )
    micro = pd.DataFrame(
        [
            _micro_row(patient_ID="1", bacteria="negative"),
            _micro_row(patient_ID="2", result_ID="002/TEST", bacteria="negative"),
            _micro_row(patient_ID="3", result_ID="003/TEST", bacteria="streptococcus gr g"),
            _micro_row(
                patient_ID="3",
                result_ID="003/TEST",
                bacteria="staphylococcus",
            ),
        ]
    )

    interpretation = build_interpretation_summary(compute_pre_swab_drugs(clinical, micro))

    assert "drug_used_before_micro" in interpretation
    assert "tobrex" in interpretation
    assert "dopasowaniu" in interpretation.lower()
    assert "bez leczenia" in interpretation.lower() or "brak leczenia" in interpretation.lower()
    assert "statusu leczenia" in interpretation.lower()


def test_treatment_status_chart_title_wraps_for_ui_and_export() -> None:
    from vetstats_app.analysis.chart_models import AnalysisChartSpec
    from vetstats_app.services.analysis_chart_renderer import (
        _chart_title_line_count,
        _formatted_chart_title,
        chart_spec_to_png_bytes,
    )

    spec = AnalysisChartSpec(
        chart_id="pre_swab_treatment_status_culture",
        title="Status leczenia przed wymazem a wynik posiewu",
        subtitle=(
            "Skumulowany rozkład wyników posiewu w dopasowanych "
            "przypadkach według statusu leczenia"
        ),
        chart_type="stacked_bar",
        labels=("Leczenie przed wymazem", "Brak leczenia przed wymazem"),
        values=(),
        stacked_series_labels=("Wynik negatywny", "Wzrost mieszany"),
        stacked_series_values=((2.0, 1.0), (1.0, 2.0)),
        x_axis_label="Status leczenia przed wymazem",
        y_axis_label="Liczba przypadków",
    )

    ui_title = _formatted_chart_title(spec, layout_mode="ui")
    export_title = _formatted_chart_title(spec, layout_mode="export")

    assert ui_title.split("\n")[0] == spec.title
    assert export_title.split("\n")[0] == spec.title
    assert _chart_title_line_count(spec, layout_mode="ui") <= 4
    assert len(chart_spec_to_png_bytes(spec)) > 500
    assert spec.subtitle.replace("\n", " ") in ui_title.replace("\n", " ")


def test_pre_swab_chart_labels_wrap_long_categories() -> None:
    from vetstats_app.analysis.chart_models import AnalysisChartSpec
    from vetstats_app.services.analysis_chart_renderer import (
        _display_category_labels,
        chart_spec_to_png_bytes,
    )

    spec = AnalysisChartSpec(
        chart_id="pre_swab_culture_outcomes",
        title="Wyniki posiewu",
        chart_type="bar",
        labels=("Pojedynczy wzrost bakteryjny", "Wzrost mieszany"),
        values=(3.0, 1.0),
        x_axis_label="Wynik posiewu",
        y_axis_label="Liczba",
    )

    wrapped = _display_category_labels(spec)
    assert any("\n" in label for label in wrapped)
    assert len(chart_spec_to_png_bytes(spec)) > 500
