"""Tests for the full VetStats combined PDF report."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from vetstats_app.analysis.report_models import (
    AnalysisSectionReport,
    CombinedAnalysisReport,
    FullVetStatsReport,
)
from vetstats_app.services.full_report_service import FullReportService
from vetstats_app.services.section_report_pdf import (
    write_combined_analysis_report_pdf,
    write_full_vetstats_report_pdf,
)


def _sample_section(title: str) -> AnalysisSectionReport:
    return AnalysisSectionReport(
        section_title=title,
        source_labels=("clinical.csv",),
        summary_details="Podsumowanie testowe.",
        interpretation_summary="Interpretacja testowa.",
        table_blocks=(),
        chart_specs=(),
    )


def _sample_combined_report() -> CombinedAnalysisReport:
    sections = (
        _sample_section("Charakterystyka populacji pacjentów"),
        _sample_section("Analiza częstości rozpoznań"),
    )
    return CombinedAnalysisReport(
        report_title="Raport analizy automatycznej",
        generation_context="Wygenerowano: 2026-06-24 12:00.",
        sections=sections,
        source_data_description="Opis źródeł testowych.",
        verbal_analysis_summary="Skrót interpretacji.",
        section_overview_rows=(
            (sections[0].section_title, "0", "0"),
            (sections[1].section_title, "0", "0"),
        ),
    )


def test_write_full_vetstats_report_pdf_creates_valid_pdf(tmp_path: Path) -> None:
    report = FullVetStatsReport(
        report_title="Raport analizy",
        generation_timestamp="2026-06-24 12:00",
        dataset_label="patient.csv (Sterile_data/patient.csv)",
        automatic_report=_sample_combined_report(),
        detailed_skipped_reason="Analiza szczegółowa pominięta: brak konfiguracji.",
        closing_summary="Podsumowanie testowe.",
    )
    destination = tmp_path / "full_report.pdf"

    write_full_vetstats_report_pdf(report, destination)

    assert destination.is_file()
    assert destination.read_bytes()[:4] == b"%PDF"


def test_write_combined_analysis_report_pdf_still_works(tmp_path: Path) -> None:
    destination = tmp_path / "combined_report.pdf"

    write_combined_analysis_report_pdf(_sample_combined_report(), destination)

    assert destination.is_file()
    assert destination.read_bytes()[:4] == b"%PDF"


def test_full_report_service_collects_section_errors(tmp_path: Path) -> None:
    combined = _sample_combined_report()
    service = FullReportService()

    with patch.object(
        service._analysis_report_service,
        "prepare_combined_automatic_analysis_report",
        return_value=(combined, (("Analiza oporności bakterii w czasie", "boom"),)),
    ):
        report = service.build_full_report(detailed_context=None)
        assert report.section_errors == (("Analiza oporności bakterii w czasie", "boom"),)
        destination = tmp_path / "full_with_warning.pdf"
        error, warnings = service.export_full_report_pdf(destination, detailed_context=None)
        assert error is None
        assert any("oporności" in warning for warning in warnings)
