from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.services.analysis_chart_renderer import (
    save_chart_spec,
    save_chart_specs_to_pdf,
)
from vetstats_app.services.app_event_logger import log_error, log_info

SUPPORTED_EXPORT_FORMATS = ("pdf", "png", "tiff")
SUPPORTED_EXPORT_DPI = (300, 600)


@dataclass(frozen=True)
class ChartExportSettings:
    file_format: str
    dpi: int


@dataclass(frozen=True)
class ChartExportOverrides:
    title: str | None = None
    x_axis_label: str | None = None
    y_axis_label: str | None = None


def apply_chart_overrides(
    chart: AnalysisChartSpec,
    overrides: ChartExportOverrides | None = None,
) -> AnalysisChartSpec:
    if overrides is None:
        return chart

    updates: dict[str, str] = {}
    if overrides.title is not None:
        cleaned_title = overrides.title.strip()
        if cleaned_title:
            updates["title"] = cleaned_title
    if overrides.x_axis_label is not None:
        updates["x_axis_label"] = overrides.x_axis_label.strip()
    if overrides.y_axis_label is not None:
        updates["y_axis_label"] = overrides.y_axis_label.strip()

    if not updates:
        return chart
    return replace(chart, **updates)


def export_all_charts(
    charts: tuple[AnalysisChartSpec, ...],
    settings: ChartExportSettings,
    destination: Path,
) -> str | None:
    if not charts:
        message = "Brak wykresów do wyeksportowania."
        log_error("chart_export", f"Eksport wielu wykresów nie powiódł się: {message}")
        return message

    if settings.file_format not in SUPPORTED_EXPORT_FORMATS:
        message = f"Nieobsługiwany format eksportu: {settings.file_format}."
        log_error("chart_export", f"Eksport wielu wykresów nie powiódł się: {message}")
        return message
    if settings.dpi not in SUPPORTED_EXPORT_DPI:
        message = f"Nieobsługiwana rozdzielczość DPI: {settings.dpi}."
        log_error("chart_export", f"Eksport wielu wykresów nie powiódł się: {message}")
        return message

    try:
        if settings.file_format == "pdf":
            save_chart_specs_to_pdf(charts, destination, dpi=settings.dpi)
        else:
            destination.mkdir(parents=True, exist_ok=True)
            for chart in charts:
                file_path = destination / _chart_filename(chart, settings.file_format)
                save_chart_spec(
                    chart,
                    file_path,
                    file_format=settings.file_format,
                    dpi=settings.dpi,
                )
    except OSError as error:
        message = f"Nie udało się zapisać wykresów: {error}"
        log_error(
            "chart_export",
            (
                f"Eksport wielu wykresów nie powiódł się "
                f"({len(charts)} wykresów, format {settings.file_format}, "
                f"DPI {settings.dpi}, cel: {destination}): {error}"
            ),
        )
        return message

    destination_label = str(destination)
    log_info(
        "chart_export",
        (
            f"Eksport wielu wykresów: {len(charts)} wykresów, "
            f"format {settings.file_format}, DPI {settings.dpi} → {destination_label}"
        ),
    )
    return None


def export_single_chart(
    chart: AnalysisChartSpec,
    settings: ChartExportSettings,
    destination: Path,
    *,
    overrides: ChartExportOverrides | None = None,
) -> str | None:
    if settings.file_format not in SUPPORTED_EXPORT_FORMATS:
        message = f"Nieobsługiwany format eksportu: {settings.file_format}."
        log_error("chart_export", f"Eksport pojedynczego wykresu nie powiódł się: {message}")
        return message
    if settings.dpi not in SUPPORTED_EXPORT_DPI:
        message = f"Nieobsługiwana rozdzielczość DPI: {settings.dpi}."
        log_error("chart_export", f"Eksport pojedynczego wykresu nie powiódł się: {message}")
        return message

    export_spec = apply_chart_overrides(chart, overrides)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if settings.file_format == "pdf" and destination.suffix.lower() != ".pdf":
            destination = destination.with_suffix(".pdf")
        save_chart_spec(
            export_spec,
            destination,
            file_format=settings.file_format,
            dpi=settings.dpi,
        )
    except OSError as error:
        message = f"Nie udało się zapisać wykresu: {error}"
        log_error(
            "chart_export",
            (
                f"Eksport pojedynczego wykresu \"{export_spec.title}\" nie powiódł się "
                f"(format {settings.file_format}, DPI {settings.dpi}, "
                f"cel: {destination}): {error}"
            ),
        )
        return message

    log_info(
        "chart_export",
        (
            f"Eksport pojedynczego wykresu: \"{export_spec.title}\", "
            f"format {settings.file_format}, DPI {settings.dpi} → {destination}"
        ),
    )
    return None


def _chart_filename(chart: AnalysisChartSpec, file_format: str) -> str:
    base = _safe_filename(chart.chart_id or chart.title)
    return f"{base}.{file_format}"


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("_")
    return cleaned[:80] if cleaned else "wykres"
