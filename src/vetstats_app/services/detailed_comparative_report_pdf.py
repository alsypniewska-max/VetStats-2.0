"""PDF export for detailed comparative analysis results."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.platypus import (
    Image,
    NextPageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
)

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.analysis.detailed_comparative_analysis import (
    DetailedComparativeAnalysisResult,
)
from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.services.section_report_pdf import (
    _build_chart_image,
    _build_report_styles,
    _build_table_block_story,
    _create_document,
    _register_unicode_font,
)

_REPORT_TITLE = "Analiza szczegółowa — porównanie grup"


def write_detailed_comparative_report_pdf(
    result: DetailedComparativeAnalysisResult,
    destination: Path,
) -> None:
    if not result.is_success:
        raise ValueError(result.error_message or "Brak wyników analizy do eksportu.")

    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")
    destination.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_unicode_font()
    styles = _build_report_styles(font_name)
    doc = _create_document(destination, _REPORT_TITLE, font_name)
    story = build_detailed_comparative_report_story(
        result,
        styles,
        font_name,
        include_top_title=True,
    )
    doc.build(story)


def build_detailed_comparative_report_story(
    result: DetailedComparativeAnalysisResult,
    styles: dict,
    font_name: str,
    *,
    include_top_title: bool = True,
) -> list:
    return _build_report_story(
        result,
        styles,
        font_name,
        include_top_title=include_top_title,
    )


def _build_report_story(
    result: DetailedComparativeAnalysisResult,
    styles: dict,
    font_name: str,
    *,
    include_top_title: bool = True,
) -> list:
    title_style = styles["title"]
    heading_style = styles["heading"]
    body_style = styles["body"]

    story: list = []
    if include_top_title:
        story.extend(
            [
                Paragraph(escape(_REPORT_TITLE), title_style),
                Spacer(1, 6),
            ]
        )

    story.append(Paragraph(escape("Opis grup"), heading_style))
    story.extend(_paragraphs_from_text(result.group_description_text, body_style))

    story.append(PageBreak())
    story.append(NextPageTemplate("portrait"))
    story.append(Paragraph(escape("Statystyka opisowa"), heading_style))
    story.extend(_paragraphs_from_text(result.descriptive_summary_text, body_style))
    story.extend(_build_descriptive_table_story(result, heading_style, body_style, font_name))

    story.append(PageBreak())
    story.append(NextPageTemplate("portrait"))
    story.append(Paragraph(escape("Analiza statystyczna"), heading_style))
    story.extend(_paragraphs_from_text(result.statistical_summary_text, body_style))
    story.extend(_paragraphs_from_text(result.interpretation_text, body_style))
    if result.warnings:
        story.append(Paragraph(escape("Ostrzeżenia"), heading_style))
        for warning in result.warnings:
            story.append(Paragraph(escape(f"• {warning}"), body_style))

    chart_story = _build_charts_story(result, heading_style, body_style)
    if chart_story:
        story.extend(chart_story)
    else:
        story.append(PageBreak())
        story.append(NextPageTemplate("portrait"))
        story.append(Paragraph(escape("Wykresy"), heading_style))
        story.append(Paragraph(escape("Brak wykresu do wyświetlenia."), body_style))

    return story


def _paragraphs_from_text(text: str, body_style) -> list:
    if not text.strip():
        return [Paragraph(escape("brak"), body_style)]
    blocks: list = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            blocks.append(Paragraph(escape(cleaned), body_style))
    return blocks or [Paragraph(escape("brak"), body_style)]


def _build_descriptive_table_story(
    result: DetailedComparativeAnalysisResult,
    heading_style,
    body_style,
    font_name: str,
) -> list:
    if result.categorical_rows:
        block = ReportTableBlock(
            title="Tabela częstości kategorii",
            columns=(
                "Kategoria",
                f"{result.group_1_name} (n)",
                f"{result.group_1_name} (%)",
                f"{result.group_2_name} (n)",
                f"{result.group_2_name} (%)",
            ),
            rows=tuple(
                (
                    row.category,
                    str(row.group_1_count),
                    f"{row.group_1_percent:.1f}",
                    str(row.group_2_count),
                    f"{row.group_2_percent:.1f}",
                )
                for row in result.categorical_rows
            ),
        )
        return _build_table_block_story(block, heading_style, body_style, font_name)

    if result.numeric_rows:
        block = ReportTableBlock(
            title="Statystyki opisowe",
            columns=(
                "Grupa",
                "n",
                "Brakujące",
                "Średnia",
                "Mediana",
                "SD",
                "Min",
                "Max",
                "Q1",
                "Q3",
            ),
            rows=tuple(
                (
                    row.group_name,
                    str(row.n),
                    str(row.missing),
                    _format_cell(row.mean),
                    _format_cell(row.median),
                    _format_cell(row.std),
                    _format_cell(row.minimum),
                    _format_cell(row.maximum),
                    _format_cell(row.percentile_25),
                    _format_cell(row.percentile_75),
                )
                for row in result.numeric_rows
            ),
        )
        return _build_table_block_story(block, heading_style, body_style, font_name)

    return []


def _build_charts_story(
    result: DetailedComparativeAnalysisResult,
    heading_style,
    body_style,
) -> list:
    renderable = [chart for chart in result.charts if chart.has_data]
    if not renderable:
        return []

    story: list = [
        NextPageTemplate("landscape"),
        PageBreak(),
        Paragraph(escape("Wykresy"), heading_style),
    ]
    for index, chart in enumerate(renderable):
        if index > 0:
            story.append(PageBreak())
        story.append(Paragraph(escape(chart.title), body_style))
        if chart.subtitle:
            story.append(Paragraph(escape(chart.subtitle), body_style))
        story.append(Spacer(1, 6))
        chart_image = _safe_chart_image(chart)
        if chart_image is not None:
            story.append(chart_image)
        else:
            story.append(
                Paragraph(
                    escape("Nie udało się wygenerować wykresu dla tego porównania."),
                    body_style,
                )
            )
    return story


def _safe_chart_image(chart: AnalysisChartSpec) -> Image | None:
    try:
        return _build_chart_image(chart)
    except Exception:
        return None


def _format_cell(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"
