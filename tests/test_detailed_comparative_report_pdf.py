"""Tests for detailed comparative PDF export."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from vetstats_app.analysis.detailed_comparative import (
    AnalysisMode,
    AnalysisTarget,
    ComparativeGroupDefinition,
    GroupCriterion,
    DetailedComparativeState,
)
from vetstats_app.analysis.detailed_comparative_analysis import (
    run_detailed_comparative_analysis,
)
from vetstats_app.services.detailed_comparative_report_pdf import (
    write_detailed_comparative_report_pdf,
)


def _state() -> DetailedComparativeState:
    return DetailedComparativeState(
        group_1=ComparativeGroupDefinition(
            default_name="Grupa 1",
            criteria=(GroupCriterion("patient", "species", "dog"),),
        ),
        group_2=ComparativeGroupDefinition(
            default_name="Grupa 2",
            criteria=(GroupCriterion("patient", "species", "cat"),),
        ),
        analysis_target=AnalysisTarget("patient", "breed", AnalysisMode.CATEGORICAL),
    )


def _datasets() -> dict[str, pd.DataFrame]:
    return {
        "patient": pd.DataFrame(
            {
                "patient_ID": ["1", "2", "3", "4"],
                "species": ["dog", "dog", "cat", "cat"],
                "breed": ["lab", "mix", "persian", "siamese"],
            }
        ),
        "clinical": pd.DataFrame({"patient_ID": ["1", "2", "3", "4"]}),
    }


def test_write_detailed_comparative_report_pdf_creates_valid_pdf(tmp_path: Path) -> None:
    result = run_detailed_comparative_analysis(_datasets(), _state())
    assert result.is_success

    report_path = tmp_path / "detailed_report.pdf"
    write_detailed_comparative_report_pdf(result, report_path)

    assert report_path.is_file()
    assert report_path.read_bytes()[:4] == b"%PDF"


def test_write_detailed_comparative_report_pdf_without_charts_still_exports(
    tmp_path: Path,
) -> None:
    result = run_detailed_comparative_analysis(_datasets(), _state())
    assert result.is_success
    result_without_charts = replace(result, charts=())

    report_path = tmp_path / "detailed_report_no_charts.pdf"
    write_detailed_comparative_report_pdf(result_without_charts, report_path)
    assert report_path.is_file()
