from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from vetstats_app.analysis.chart_models import AnalysisChartSpec

if TYPE_CHECKING:
    from vetstats_app.analysis.detailed_comparative_analysis import (
        DetailedComparativeAnalysisResult,
    )


@dataclass(frozen=True)
class ReportTableBlock:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class AnalysisSectionPayload:
    section_title: str
    source_labels: tuple[str, ...]
    summary_details: str
    interpretation_summary: str
    table_blocks: tuple[ReportTableBlock, ...]
    chart_specs: tuple[AnalysisChartSpec, ...] = ()


@dataclass(frozen=True)
class AnalysisSectionReport:
    section_title: str
    source_labels: tuple[str, ...]
    summary_details: str
    interpretation_summary: str
    table_blocks: tuple[ReportTableBlock, ...]
    chart_specs: tuple[AnalysisChartSpec, ...] = ()
    export_format: str = "pdf-placeholder"

    @property
    def table_count(self) -> int:
        return len(self.table_blocks)

    @property
    def row_count(self) -> int:
        return sum(len(block.rows) for block in self.table_blocks)


@dataclass(frozen=True)
class CombinedAnalysisReport:
    report_title: str
    generation_context: str
    sections: tuple[AnalysisSectionReport, ...]
    source_data_description: str = ""
    applied_filters: str = ""
    dataset_dimensions: str = ""
    verbal_analysis_summary: str = ""
    section_overview_rows: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class FullVetStatsReport:
    """Master report combining automatic analysis modules and detailed analysis."""

    report_title: str
    generation_timestamp: str
    dataset_label: str
    automatic_report: CombinedAnalysisReport
    detailed_result: DetailedComparativeAnalysisResult | None = None
    detailed_skipped_reason: str = ""
    closing_summary: str = ""
    section_errors: tuple[tuple[str, str], ...] = ()
