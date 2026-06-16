from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from vetstats_app.analysis.report_models import (
    AnalysisSectionReport,
    CombinedAnalysisReport,
    ReportTableBlock,
)


def write_section_report_pdf(report: AnalysisSectionReport, destination: Path) -> None:
    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")

    destination.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_unicode_font()
    styles = _build_report_styles(font_name)
    doc = _create_document(destination, report.section_title)
    story = _build_section_story(report, styles, font_name)
    doc.build(story)


def write_combined_analysis_report_pdf(
    report: CombinedAnalysisReport,
    destination: Path,
) -> None:
    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")

    destination.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_unicode_font()
    styles = _build_report_styles(font_name)
    doc = _create_document(destination, report.report_title)

    story: list = [
        Paragraph(escape(report.report_title), styles["cover_title"]),
        Spacer(1, 8),
        Paragraph(escape(report.generation_context), styles["body"]),
    ]

    if report.sections:
        story.append(Spacer(1, 8))
        story.append(Paragraph(escape("Zawarte sekcje"), styles["heading"]))
        for section in report.sections:
            story.append(Paragraph(escape(f"• {section.section_title}"), styles["body"]))

    for index, section in enumerate(report.sections):
        story.append(PageBreak())
        story.extend(_build_section_story(section, styles, font_name))

    doc.build(story)


def _create_document(destination: Path, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
    )


def _build_report_styles(font_name: str) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CombinedCoverTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=18,
            leading=22,
            spaceAfter=8,
        ),
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=16,
            leading=20,
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            spaceAfter=6,
        ),
    }


def _build_section_story(
    report: AnalysisSectionReport,
    styles: dict[str, ParagraphStyle],
    font_name: str,
) -> list:
    title_style = styles["title"]
    heading_style = styles["heading"]
    body_style = styles["body"]

    story: list = [
        Paragraph(escape(report.section_title), title_style),
        Spacer(1, 6),
        Paragraph(escape("Źródła danych"), heading_style),
    ]

    if report.source_labels:
        for label in report.source_labels:
            story.append(Paragraph(escape(f"• {label}"), body_style))
    else:
        story.append(Paragraph(escape("brak"), body_style))

    story.extend(
        [
            Paragraph(escape("Podsumowanie"), heading_style),
            Paragraph(escape(report.summary_details or "brak"), body_style),
            Paragraph(escape("Interpretacja"), heading_style),
            Paragraph(escape(report.interpretation_summary or "brak"), body_style),
        ]
    )

    for block in report.table_blocks:
        story.extend(_build_table_block_story(block, heading_style, body_style, font_name))

    return story


def _build_table_block_story(
    block: ReportTableBlock,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
    font_name: str,
) -> list:
    story: list = [
        Paragraph(escape(block.title), heading_style),
    ]

    if not block.columns:
        story.append(Paragraph(escape("brak kolumn"), body_style))
        return story

    table_data = [list(block.columns)]
    if block.rows:
        for row in block.rows:
            padded = list(row) + [""] * (len(block.columns) - len(row))
            table_data.append(list(padded[: len(block.columns)]))
    else:
        table_data.append([""] * len(block.columns))

    column_count = len(block.columns)
    available_width = A4[0] - 36 * mm
    column_width = available_width / column_count

    table = Table(table_data, colWidths=[column_width] * column_count, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 8))
    return story


def _register_unicode_font() -> str:
    fonts_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    candidates = (
        ("DejaVuSans", fonts_dir / "DejaVuSans.ttf"),
        ("Vera", fonts_dir / "Vera.ttf"),
    )
    for font_name, font_path in candidates:
        if not font_path.is_file():
            continue
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        return font_name
    return "Helvetica"
