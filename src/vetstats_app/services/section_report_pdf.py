from __future__ import annotations

import io
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.analysis.report_models import (
    AnalysisSectionReport,
    CombinedAnalysisReport,
    FullVetStatsReport,
    ReportTableBlock,
)
from vetstats_app.services.analysis_chart_renderer import chart_spec_to_png_bytes
from vetstats_app.services.branding import (
    APP_REPORT_TITLE,
    footer_text,
    microbiology_logo_path,
    vetstats_logo_path,
)

_HORIZONTAL_MARGIN = 18 * mm
_TOP_MARGIN = 30 * mm
_BOTTOM_MARGIN = 16 * mm
_LOGO_MAX_HEIGHT = 13 * mm
_HEADER_TITLE_FONT_SIZE = 11
_FOOTER_FONT_SIZE = 8.5
_PORTRAIT_PAGE_SIZE = A4
_LANDSCAPE_PAGE_SIZE = landscape(A4)


def write_section_report_pdf(report: AnalysisSectionReport, destination: Path) -> None:
    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")

    destination.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_unicode_font()
    styles = _build_report_styles(font_name)
    doc = _create_document(destination, report.section_title, font_name)
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
    doc = _create_document(destination, report.report_title, font_name)
    story = _build_combined_report_story(report, styles, font_name)
    doc.build(story)


def write_full_vetstats_report_pdf(
    report: FullVetStatsReport,
    destination: Path,
) -> None:
    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")

    destination.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_unicode_font()
    styles = _build_report_styles(font_name)
    doc = _create_document(destination, report.report_title, font_name)

    story: list = []
    story.extend(
        _build_title_page_story(
            report_title=report.report_title,
            generation_timestamp=report.generation_timestamp,
            dataset_label=report.dataset_label,
            styles=styles,
        )
    )
    story.extend(_build_combined_report_story(report.automatic_report, styles, font_name))

    if report.detailed_result is not None and report.detailed_result.is_success:
        from vetstats_app.services.detailed_comparative_report_pdf import (
            build_detailed_comparative_report_story,
        )

        story.append(NextPageTemplate("portrait"))
        story.append(PageBreak())
        story.append(
            Paragraph(escape("Analiza szczegółowa"), styles["title"]),
        )
        story.append(Spacer(1, 6))
        story.extend(
            build_detailed_comparative_report_story(
                report.detailed_result,
                styles,
                font_name,
                include_top_title=False,
            )
        )
    elif report.detailed_skipped_reason:
        story.extend(
            _build_skipped_section_story(
                "Analiza szczegółowa",
                report.detailed_skipped_reason,
                styles,
            )
        )

    if report.section_errors:
        story.extend(
            _build_section_errors_story(report.section_errors, styles),
        )

    story.extend(
        _build_closing_section_story(
            report.closing_summary,
            styles,
        )
    )

    doc.build(story)


def _build_combined_report_story(
    report: CombinedAnalysisReport,
    styles: dict[str, ParagraphStyle],
    font_name: str,
) -> list:
    story: list = [
        Paragraph(escape(report.report_title), styles["cover_title"]),
        Spacer(1, 8),
        Paragraph(escape(report.generation_context), styles["body"]),
    ]

    if report.source_data_description:
        story.extend(
            [
                Spacer(1, 6),
                Paragraph(escape("Opis źródeł danych"), styles["heading"]),
                Paragraph(escape(report.source_data_description), styles["body"]),
            ]
        )

    if report.applied_filters:
        story.extend(
            [
                Spacer(1, 4),
                Paragraph(escape("Zastosowane filtry"), styles["heading"]),
                Paragraph(escape(report.applied_filters), styles["body"]),
            ]
        )

    if report.dataset_dimensions:
        story.extend(
            [
                Spacer(1, 4),
                Paragraph(escape("Wymiary zbiorów danych"), styles["heading"]),
                Paragraph(escape(report.dataset_dimensions), styles["body"]),
            ]
        )

    if report.verbal_analysis_summary:
        story.extend(
            [
                Spacer(1, 4),
                Paragraph(escape("Podsumowanie werbalne"), styles["heading"]),
                Paragraph(escape(report.verbal_analysis_summary), styles["body"]),
            ]
        )

    if report.section_overview_rows:
        story.extend(
            [
                Spacer(1, 4),
                Paragraph(escape("Przegląd sekcji raportu"), styles["heading"]),
            ]
        )
        story.extend(
            _build_table_block_story(
                ReportTableBlock(
                    title="",
                    columns=("Sekcja", "Tabele", "Wiersze w tabelach"),
                    rows=report.section_overview_rows,
                ),
                styles["heading"],
                styles["body"],
                font_name,
            )
        )

    if report.sections:
        story.append(Spacer(1, 8))
        story.append(Paragraph(escape("Zawarte sekcje"), styles["heading"]))
        for section in report.sections:
            story.append(Paragraph(escape(f"• {section.section_title}"), styles["body"]))

    story.extend(_build_analysis_sections_story(report.sections, styles, font_name))
    return story


def _build_title_page_story(
    *,
    report_title: str,
    generation_timestamp: str,
    dataset_label: str,
    styles: dict[str, ParagraphStyle],
) -> list:
    story: list = [Spacer(1, 36)]

    logo_path = vetstats_logo_path()
    if logo_path.is_file():
        logo = Image(str(logo_path))
        max_width = 70 * mm
        aspect = logo.imageHeight / logo.imageWidth if logo.imageWidth else 1.0
        logo.drawWidth = max_width
        logo.drawHeight = max_width * aspect
        available_width = _PORTRAIT_PAGE_SIZE[0] - (2 * _HORIZONTAL_MARGIN)
        logo_table = Table(
            [[logo]],
            colWidths=[available_width],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
        )
        story.append(logo_table)
        story.append(Spacer(1, 18))

    story.extend(
        [
            Paragraph(escape("VetStats 2.0"), styles["cover_app_name"]),
            Paragraph(escape(report_title), styles["cover_title"]),
            Spacer(1, 10),
            Paragraph(
                escape(f"Data wygenerowania: {generation_timestamp}"),
                styles["cover_meta"],
            ),
        ]
    )

    if dataset_label:
        story.append(
            Paragraph(escape(f"Źródło danych: {dataset_label}"), styles["cover_meta"])
        )

    story.append(PageBreak())
    return story


def _build_analysis_sections_story(
    sections: tuple[AnalysisSectionReport, ...],
    styles: dict[str, ParagraphStyle],
    font_name: str,
) -> list:
    story: list = []
    for section in sections:
        story.append(NextPageTemplate("portrait"))
        story.append(PageBreak())
        story.extend(_build_section_story(section, styles, font_name))
    return story


def _build_skipped_section_story(
    section_title: str,
    reason: str,
    styles: dict[str, ParagraphStyle],
) -> list:
    return [
        NextPageTemplate("portrait"),
        PageBreak(),
        Paragraph(escape(section_title), styles["title"]),
        Spacer(1, 6),
        Paragraph(escape(reason), styles["body"]),
    ]


def _build_section_errors_story(
    section_errors: tuple[tuple[str, str], ...],
    styles: dict[str, ParagraphStyle],
) -> list:
    story: list = [
        NextPageTemplate("portrait"),
        PageBreak(),
        Paragraph(escape("Uwagi do sekcji raportu"), styles["title"]),
        Spacer(1, 6),
    ]
    for section_title, message in section_errors:
        story.append(
            Paragraph(
                escape(f"{section_title}: {message}"),
                styles["body"],
            )
        )
    return story


def _build_closing_section_story(
    closing_summary: str,
    styles: dict[str, ParagraphStyle],
) -> list:
    summary = closing_summary.strip() or (
        "Raport łączy wyniki analizy automatycznej oraz — jeśli skonfigurowano — "
        "analizę szczegółową porównania grup. Szczegółowe tabele, interpretacje "
        "i wykresy znajdują się w poprzednich sekcjach dokumentu."
    )
    return [
        NextPageTemplate("portrait"),
        PageBreak(),
        Paragraph(escape("Podsumowanie końcowe"), styles["title"]),
        Spacer(1, 6),
        Paragraph(escape(summary), styles["body"]),
    ]


def _create_document(destination: Path, title: str, font_name: str) -> BaseDocTemplate:
    draw_page_branding = _make_draw_page_branding(font_name)
    doc = BaseDocTemplate(
        str(destination),
        pagesize=_PORTRAIT_PAGE_SIZE,
        leftMargin=_HORIZONTAL_MARGIN,
        rightMargin=_HORIZONTAL_MARGIN,
        topMargin=_TOP_MARGIN,
        bottomMargin=_BOTTOM_MARGIN,
        title=title,
    )
    portrait_frame = Frame(
        _HORIZONTAL_MARGIN,
        _BOTTOM_MARGIN,
        _PORTRAIT_PAGE_SIZE[0] - (2 * _HORIZONTAL_MARGIN),
        _PORTRAIT_PAGE_SIZE[1] - _TOP_MARGIN - _BOTTOM_MARGIN,
        id="portrait_frame",
    )
    landscape_frame = Frame(
        _HORIZONTAL_MARGIN,
        _BOTTOM_MARGIN,
        _LANDSCAPE_PAGE_SIZE[0] - (2 * _HORIZONTAL_MARGIN),
        _LANDSCAPE_PAGE_SIZE[1] - _TOP_MARGIN - _BOTTOM_MARGIN,
        id="landscape_frame",
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="portrait",
                frames=[portrait_frame],
                pagesize=_PORTRAIT_PAGE_SIZE,
                onPage=draw_page_branding,
            ),
            PageTemplate(
                id="landscape",
                frames=[landscape_frame],
                pagesize=_LANDSCAPE_PAGE_SIZE,
                onPage=draw_page_branding,
            ),
        ]
    )
    return doc


def _make_draw_page_branding(font_name: str):
    left_logo = _load_logo_reader(vetstats_logo_path())
    right_logo = _load_logo_reader(microbiology_logo_path())
    footer = footer_text()

    def _draw_page_branding(canvas, doc) -> None:
        page_width, page_height = canvas._pagesize
        canvas.saveState()

        header_bottom = page_height - _TOP_MARGIN
        logo_y = header_bottom + (_TOP_MARGIN - _LOGO_MAX_HEIGHT) / 2
        title_y = logo_y + (_LOGO_MAX_HEIGHT / 2) - (_HEADER_TITLE_FONT_SIZE / 3)

        _draw_logo(
            canvas,
            left_logo,
            x=_HORIZONTAL_MARGIN,
            y=logo_y,
            max_height=_LOGO_MAX_HEIGHT,
            anchor="left",
        )
        _draw_logo(
            canvas,
            right_logo,
            x=page_width - _HORIZONTAL_MARGIN,
            y=logo_y,
            max_height=_LOGO_MAX_HEIGHT,
            anchor="right",
        )

        canvas.setFont(font_name, _HEADER_TITLE_FONT_SIZE)
        canvas.setFillColor(colors.HexColor("#1F2937"))
        canvas.drawCentredString(page_width / 2, title_y, APP_REPORT_TITLE)

        canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        canvas.setLineWidth(0.5)
        canvas.line(
            _HORIZONTAL_MARGIN,
            header_bottom,
            page_width - _HORIZONTAL_MARGIN,
            header_bottom,
        )

        footer_y = _BOTTOM_MARGIN / 2 - (_FOOTER_FONT_SIZE / 3)
        canvas.setFont(font_name, _FOOTER_FONT_SIZE)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawCentredString(page_width / 2, footer_y, footer)

        canvas.restoreState()

    return _draw_page_branding


def _load_logo_reader(path: Path):
    if not path.is_file():
        return None
    try:
        from reportlab.lib.utils import ImageReader

        return ImageReader(str(path))
    except Exception:
        return None


def _draw_logo(
    canvas,
    image_reader,
    *,
    x: float,
    y: float,
    max_height: float,
    anchor: str,
) -> None:
    if image_reader is None:
        return
    try:
        image_width, image_height = image_reader.getSize()
        if image_width <= 0 or image_height <= 0:
            return
        draw_height = max_height
        draw_width = draw_height * (image_width / image_height)
        draw_x = x if anchor == "left" else x - draw_width
        canvas.drawImage(
            image_reader,
            draw_x,
            y,
            width=draw_width,
            height=draw_height,
            mask="auto",
            preserveAspectRatio=True,
        )
    except Exception:
        return


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
            alignment=1,
        ),
        "cover_app_name": ParagraphStyle(
            "CombinedCoverAppName",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=22,
            leading=26,
            spaceAfter=6,
            alignment=1,
            textColor=colors.HexColor("#1F2937"),
        ),
        "cover_meta": ParagraphStyle(
            "CombinedCoverMeta",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=15,
            spaceAfter=4,
            alignment=1,
            textColor=colors.HexColor("#4B5563"),
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

    story.extend(_build_section_chart_story(report, heading_style, body_style))
    return story


def _chart_spec_renderable(spec: AnalysisChartSpec) -> bool:
    return spec.has_data


def _build_section_chart_story(
    report: AnalysisSectionReport,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> list:
    renderable_charts = tuple(
        chart for chart in report.chart_specs if _chart_spec_renderable(chart)
    )
    if not renderable_charts:
        return []

    story: list = [
        NextPageTemplate("landscape"),
        PageBreak(),
        Paragraph(escape("Wykresy"), heading_style),
    ]

    for index, chart in enumerate(renderable_charts):
        if index > 0:
            story.append(PageBreak())
        story.append(Paragraph(escape(chart.title), body_style))
        story.append(Spacer(1, 6))
        story.append(_build_chart_image(chart))

    return story


def _build_chart_image(chart: AnalysisChartSpec) -> Image:
    png_bytes = chart_spec_to_png_bytes(
        chart,
        width_inches=9.0,
        height_inches=5.0,
        dpi=120,
    )
    image = Image(io.BytesIO(png_bytes))
    max_width = _LANDSCAPE_PAGE_SIZE[0] - (2 * _HORIZONTAL_MARGIN)
    max_height = (
        _LANDSCAPE_PAGE_SIZE[1] - _TOP_MARGIN - _BOTTOM_MARGIN - (20 * mm)
    )
    aspect = image.imageHeight / image.imageWidth if image.imageWidth else 1.0
    image.drawWidth = max_width
    image.drawHeight = max_width * aspect
    if image.drawHeight > max_height:
        image.drawHeight = max_height
        image.drawWidth = max_height / aspect
    return image


def _build_table_block_story(
    block: ReportTableBlock,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
    font_name: str,
) -> list:
    story: list = []
    if block.title:
        story.append(Paragraph(escape(block.title), heading_style))

    if not block.columns:
        story.append(Paragraph(escape("brak kolumn"), body_style))
        return story

    column_count = len(block.columns)

    header_cell_style = ParagraphStyle(
        "TableHeaderCell",
        parent=body_style,
        fontName=font_name,
        fontSize=8.5,
        leading=10.5,
        spaceAfter=0,
        textColor=colors.black,
    )
    body_cell_style = ParagraphStyle(
        "TableBodyCell",
        parent=body_style,
        fontName=font_name,
        fontSize=8.5,
        leading=10.5,
        spaceAfter=0,
    )

    def _cell(text: object, style: ParagraphStyle) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    raw_rows: list[tuple[str, ...]] = []
    if block.rows:
        for row in block.rows:
            padded = list(row) + [""] * (column_count - len(row))
            raw_rows.append(tuple(padded[:column_count]))
    else:
        raw_rows.append(tuple([""] * column_count))

    table_data = [[_cell(col, header_cell_style) for col in block.columns]]
    for row in raw_rows:
        table_data.append([_cell(value, body_cell_style) for value in row])

    available_width = _PORTRAIT_PAGE_SIZE[0] - (2 * _HORIZONTAL_MARGIN)
    column_widths = _proportional_column_widths(
        block.columns, raw_rows, available_width
    )

    table = Table(table_data, colWidths=column_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
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


def _proportional_column_widths(
    columns: tuple[str, ...],
    rows: list[tuple[str, ...]],
    available_width: float,
) -> list[float]:
    column_count = len(columns)
    max_lengths: list[int] = []
    for column_index in range(column_count):
        longest = len(str(columns[column_index]))
        for row in rows:
            if column_index < len(row):
                longest = max(longest, len(str(row[column_index])))
        max_lengths.append(max(longest, 1))

    total_length = sum(max_lengths)
    min_width = available_width * 0.07
    raw_widths = [available_width * (length / total_length) for length in max_lengths]
    clamped = [max(width, min_width) for width in raw_widths]
    scale = available_width / sum(clamped)
    return [width * scale for width in clamped]


def _register_unicode_font() -> str:
    fonts_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    candidates = (
        ("DejaVuSans", fonts_dir / "DejaVuSans.ttf"),
        ("DejaVuSans", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")),
        ("ArialUnicode", Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")),
        ("ArialUnicode", Path("/Library/Fonts/Arial Unicode.ttf")),
        ("Arial", Path("/System/Library/Fonts/Supplemental/Arial.ttf")),
        ("Arial", Path("C:/Windows/Fonts/arial.ttf")),
        ("DejaVuSans", Path("/usr/share/fonts/dejavu/DejaVuSans.ttf")),
        ("Vera", fonts_dir / "Vera.ttf"),
    )
    for font_name, font_path in candidates:
        if not font_path.is_file():
            continue
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        return font_name
    return "Helvetica"
