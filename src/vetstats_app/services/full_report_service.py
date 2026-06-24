"""Orchestrates the full VetStats PDF report (automatic + detailed analysis)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from vetstats_app.analysis.detailed_comparative import DetailedComparativeState
from vetstats_app.analysis.detailed_comparative_analysis import (
    DetailedComparativeAnalysisResult,
)
from vetstats_app.analysis.report_models import FullVetStatsReport
from vetstats_app.services.analysis_report_service import (
    AnalysisReportService,
    resolve_dataset_label,
)
from vetstats_app.services.app_event_logger import log_error, log_info
from vetstats_app.services.detailed_comparative_service import DetailedComparativeService
from vetstats_app.services.section_report_pdf import write_full_vetstats_report_pdf

ProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True)
class DetailedAnalysisContext:
    state: DetailedComparativeState
    last_result: DetailedComparativeAnalysisResult | None = None


class FullReportService:
    def __init__(
        self,
        analysis_report_service: AnalysisReportService | None = None,
        detailed_service: DetailedComparativeService | None = None,
    ) -> None:
        self._analysis_report_service = (
            analysis_report_service or AnalysisReportService()
        )
        self._detailed_service = detailed_service or DetailedComparativeService()

    def build_full_report(
        self,
        *,
        detailed_context: DetailedAnalysisContext | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> FullVetStatsReport:
        automatic_report, section_errors = (
            self._analysis_report_service.prepare_combined_automatic_analysis_report(
                progress_callback=progress_callback,
            )
        )

        detailed_result: DetailedComparativeAnalysisResult | None = None
        detailed_skipped_reason = ""
        if detailed_context is not None:
            detailed_step = len(automatic_report.sections) + 1
            total_steps = detailed_step
            if progress_callback is not None:
                progress_callback("Analiza szczegółowa", detailed_step, total_steps)
            detailed_result, detailed_skipped_reason = self._resolve_detailed_result(
                detailed_context
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        closing_summary = self._build_closing_summary(
            len(automatic_report.sections),
            detailed_result is not None,
            section_errors,
        )

        return FullVetStatsReport(
            report_title="Raport analizy",
            generation_timestamp=timestamp,
            dataset_label=resolve_dataset_label(),
            automatic_report=automatic_report,
            detailed_result=detailed_result,
            detailed_skipped_reason=detailed_skipped_reason,
            closing_summary=closing_summary,
            section_errors=section_errors,
        )

    def export_full_report_pdf(
        self,
        destination: Path,
        *,
        detailed_context: DetailedAnalysisContext | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[str | None, list[str]]:
        warnings: list[str] = []
        try:
            report = self.build_full_report(
                detailed_context=detailed_context,
                progress_callback=progress_callback,
            )
            write_full_vetstats_report_pdf(report, destination)
        except OSError as exc:
            message = f"Nie udało się zapisać raportu PDF: {exc}"
            log_error("full_report", message)
            return message, warnings
        except Exception as exc:
            message = f"Nie udało się wygenerować pełnego raportu PDF: {exc}"
            log_error("full_report", message)
            return message, warnings

        for section_title, error_message in report.section_errors:
            warnings.append(f"{section_title}: {error_message}")
        if report.detailed_skipped_reason:
            warnings.append(report.detailed_skipped_reason)

        log_info(
            "full_report",
            f"Wyeksportowano pełny raport PDF → {Path(destination).name}",
        )
        return None, warnings

    def _resolve_detailed_result(
        self,
        context: DetailedAnalysisContext,
    ) -> tuple[DetailedComparativeAnalysisResult | None, str]:
        validation = self._detailed_service.validate(context.state)
        if not validation.can_analyze:
            messages = list(validation.blocking_messages)
            if validation.status_message and not messages:
                messages.append(validation.status_message)
            reason = "Analiza szczegółowa pominięta: " + " ".join(messages)
            return None, reason

        result = self._detailed_service.analyze(context.state)
        if not result.is_success:
            return None, result.error_message or "Analiza szczegółowa nie powiodła się."
        return result, ""

    def _build_closing_summary(
        self,
        automatic_section_count: int,
        detailed_included: bool,
        section_errors: tuple[tuple[str, str], ...],
    ) -> str:
        parts = [
            (
                f"Raport obejmuje {automatic_section_count} sekcji analizy automatycznej "
                "wraz z tabelami, interpretacjami i wykresami."
            ),
        ]
        if detailed_included:
            parts.append(
                "Dołączono analizę szczegółową porównania grup zgodnie z bieżącą "
                "konfiguracją w zakładce Analysis."
            )
        else:
            parts.append(
                "Analiza szczegółowa nie została dołączona — skonfiguruj grupy i zmienną "
                "w zakładce Analysis, a następnie wygeneruj raport ponownie."
            )
        if section_errors:
            parts.append(
                f"Uwaga: {len(section_errors)} sekcji automatycznych wymagało obsługi błędu; "
                "szczegóły znajdują się w odpowiednich rozdziałach raportu."
            )
        return " ".join(parts)
