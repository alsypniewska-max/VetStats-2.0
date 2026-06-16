from __future__ import annotations

from dataclasses import dataclass


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


@dataclass(frozen=True)
class AnalysisSectionReport:
    section_title: str
    source_labels: tuple[str, ...]
    summary_details: str
    interpretation_summary: str
    table_blocks: tuple[ReportTableBlock, ...]
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
