from __future__ import annotations

from pathlib import Path

from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_CODE_MAPPING,
    DiagnosisFrequencyResult,
    build_interpretation_summary as build_diagnosis_frequency_interpretation,
)
from vetstats_app.analysis.treatment_groups import (
    TreatmentCategoryRow,
    TreatmentGroupsResult,
    build_interpretation_summary as build_treatment_groups_interpretation,
    build_summary_details as build_treatment_groups_summary_details,
)
from vetstats_app.analysis.patient_id_cross_table_summary import (
    PatientIdCrossTableSummaryResult,
    build_interpretation_summary as build_patient_id_cross_table_interpretation,
    build_summary_details as build_patient_id_cross_table_summary_details,
)
from vetstats_app.analysis.diagnosis_culture_relationship import (
    DiagnosisCultureRelationshipResult,
    build_interpretation_summary as build_diagnosis_culture_interpretation,
    build_matching_details as build_diagnosis_culture_matching_details,
    build_summary_details as build_diagnosis_culture_summary_details,
)
from vetstats_app.analysis.procedure_diagnosis_relationship import (
    ProcedureDiagnosisRelationshipResult,
    build_interpretation_summary as build_procedure_diagnosis_interpretation,
    build_summary_details as build_procedure_diagnosis_summary_details,
    build_table_details as build_procedure_diagnosis_table_details,
    format_top_diagnoses,
    observed_procedure_categories,
)
from vetstats_app.analysis.treatment_diagnosis_relationship import (
    TreatmentDiagnosisRelationshipResult,
    build_interpretation_summary as build_treatment_diagnosis_interpretation,
    build_summary_details as build_treatment_diagnosis_summary_details,
    build_table_details as build_treatment_diagnosis_table_details,
    format_top_ulcer_categories,
    observed_treatment_categories,
)
from vetstats_app.analysis.microbiology_results import (
    MicrobiologyResultsResult,
    build_interpretation_summary as build_microbiology_results_interpretation,
    build_matching_details as build_microbiology_results_matching_details,
    build_summary_details as build_microbiology_results_summary_details,
)
from datetime import datetime

from vetstats_app.analysis.report_models import (
    AnalysisSectionPayload,
    AnalysisSectionReport,
    CombinedAnalysisReport,
    ReportTableBlock,
)
from vetstats_app.services.diagnosis_culture_relationship_service import (
    DiagnosisCultureRelationshipService,
)
from vetstats_app.services.diagnosis_frequency_service import DiagnosisFrequencyService
from vetstats_app.services.patient_id_cross_table_summary_service import (
    PatientIdCrossTableSummaryService,
)
from vetstats_app.services.section_report_pdf import (
    write_combined_analysis_report_pdf,
    write_section_report_pdf,
)
from vetstats_app.services.microbiology_results_service import MicrobiologyResultsService
from vetstats_app.services.procedure_diagnosis_relationship_service import (
    ProcedureDiagnosisRelationshipService,
)
from vetstats_app.services.treatment_diagnosis_relationship_service import (
    TreatmentDiagnosisRelationshipService,
)
from vetstats_app.services.treatment_groups_service import TreatmentGroupsService


class AnalysisReportService:
    def build_section_report(
        self,
        payload: AnalysisSectionPayload,
    ) -> AnalysisSectionReport:
        return AnalysisSectionReport(
            section_title=payload.section_title.strip(),
            source_labels=tuple(label.strip() for label in payload.source_labels if label.strip()),
            summary_details=payload.summary_details.strip(),
            interpretation_summary=payload.interpretation_summary.strip(),
            table_blocks=tuple(
                ReportTableBlock(
                    title=block.title.strip(),
                    columns=tuple(column.strip() for column in block.columns),
                    rows=tuple(
                        tuple(str(value).strip() for value in row)
                        for row in block.rows
                    ),
                )
                for block in payload.table_blocks
            ),
        )

    def build_diagnosis_frequency_payload(
        self,
        result: DiagnosisFrequencyResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Analiza częstości rozpoznań",
            source_labels=(result.source_label,),
            summary_details=_build_diagnosis_frequency_summary_details(result),
            interpretation_summary=build_diagnosis_frequency_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Mapowanie kodów rozpoznań",
                    columns=("Kod", "Rozpoznanie"),
                    rows=tuple(
                        (code, diagnosis)
                        for code, diagnosis in DIAGNOSIS_CODE_MAPPING
                    ),
                ),
                ReportTableBlock(
                    title="Częstość rozpoznań",
                    columns=("Kod", "Rozpoznanie", "Liczba", "Udział (%)"),
                    rows=tuple(
                        (
                            row.code,
                            row.label,
                            str(row.count),
                            f"{row.percentage:.1f}",
                        )
                        for row in result.frequencies
                    ),
                ),
            ),
        )

    def build_treatment_groups_payload(
        self,
        result: TreatmentGroupsResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Analiza leczenia w grupach pacjentów",
            source_labels=(result.source_label,),
            summary_details=_build_treatment_groups_summary_details(result),
            interpretation_summary=build_treatment_groups_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Podział przypadków według typu leczenia (farmacology_surgery)",
                    columns=("Kod", "Kategoria", "Liczba", "Udział (%)"),
                    rows=_treatment_category_rows(result.pharmacology_rows),
                ),
                ReportTableBlock(
                    title="Leczenie miejscowe i ogólne (topical_systemic)",
                    columns=("Kod", "Kategoria", "Liczba", "Udział (%)"),
                    rows=_treatment_category_rows(result.topical_rows),
                ),
                ReportTableBlock(
                    title="Skuteczność leczenia wrzodów",
                    columns=("Metryka", "Wartość"),
                    rows=_ulcer_success_rows(result),
                ),
            ),
        )

    def build_microbiology_results_payload(
        self,
        result: MicrobiologyResultsResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Analiza wyników mikrobiologicznych",
            source_labels=(
                result.source_clinical_label,
                result.source_micro_label,
            ),
            summary_details=_build_microbiology_results_summary_details(result),
            interpretation_summary=build_microbiology_results_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Najczęściej izolowane bakterie i wyniki negatywne",
                    columns=("Bakteria", "Liczba", "Udział (%)"),
                    rows=_microbiology_bacteria_rows(result),
                ),
            ),
        )

    def prepare_microbiology_results_report(
        self,
        result: MicrobiologyResultsResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_microbiology_results_payload(result)
        )

    def export_microbiology_results_report_pdf(
        self,
        result: MicrobiologyResultsResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_microbiology_results_report(result)
        return self.export_section_report_pdf(report, destination)

    def build_diagnosis_culture_relationship_payload(
        self,
        result: DiagnosisCultureRelationshipResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Powiązanie rozpoznań z wynikami posiewu",
            source_labels=(
                result.source_clinical_label,
                result.source_micro_label,
            ),
            summary_details=_build_diagnosis_culture_summary_details(result),
            interpretation_summary=build_diagnosis_culture_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Przypadki według kategorii wrzodu",
                    columns=("Kod", "Kategoria wrzodu", "Liczba przypadków"),
                    rows=_diagnosis_culture_category_rows(result),
                ),
                ReportTableBlock(
                    title="Bakterie w poszczególnych kategoriach wrzodu",
                    columns=("Kategoria wrzodu", "Bakteria", "Liczba"),
                    rows=_diagnosis_culture_bacteria_rows(result),
                ),
            ),
        )

    def prepare_diagnosis_culture_relationship_report(
        self,
        result: DiagnosisCultureRelationshipResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_diagnosis_culture_relationship_payload(result)
        )

    def export_diagnosis_culture_relationship_report_pdf(
        self,
        result: DiagnosisCultureRelationshipResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_diagnosis_culture_relationship_report(result)
        return self.export_section_report_pdf(report, destination)

    def build_procedure_diagnosis_relationship_payload(
        self,
        result: ProcedureDiagnosisRelationshipResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Powiązanie type_of_surgery z type_of_ulcer",
            source_labels=(result.source_label,),
            summary_details=_build_procedure_diagnosis_summary_details(result),
            interpretation_summary=build_procedure_diagnosis_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Powiązanie type_of_surgery z type_of_ulcer",
                    columns=(
                        "Kod type_of_surgery",
                        "Kategoria procedury",
                        "Liczba wierszy",
                        "Najczęstsze kategorie type_of_ulcer",
                    ),
                    rows=_procedure_diagnosis_relationship_rows(result),
                ),
            ),
        )

    def prepare_procedure_diagnosis_relationship_report(
        self,
        result: ProcedureDiagnosisRelationshipResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_procedure_diagnosis_relationship_payload(result)
        )

    def export_procedure_diagnosis_relationship_report_pdf(
        self,
        result: ProcedureDiagnosisRelationshipResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_procedure_diagnosis_relationship_report(result)
        return self.export_section_report_pdf(report, destination)

    def build_treatment_diagnosis_relationship_payload(
        self,
        result: TreatmentDiagnosisRelationshipResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Powiązanie topical_systemic z type_of_ulcer",
            source_labels=(result.source_label,),
            summary_details=_build_treatment_diagnosis_summary_details(result),
            interpretation_summary=build_treatment_diagnosis_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Powiązanie topical_systemic z type_of_ulcer",
                    columns=(
                        "Kod topical_systemic",
                        "Kategoria leczenia",
                        "Liczba wierszy",
                        "Najczęstsze kategorie type_of_ulcer",
                    ),
                    rows=_treatment_diagnosis_relationship_rows(result),
                ),
            ),
        )

    def prepare_treatment_diagnosis_relationship_report(
        self,
        result: TreatmentDiagnosisRelationshipResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_treatment_diagnosis_relationship_payload(result)
        )

    def export_treatment_diagnosis_relationship_report_pdf(
        self,
        result: TreatmentDiagnosisRelationshipResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_treatment_diagnosis_relationship_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_treatment_groups_report(
        self,
        result: TreatmentGroupsResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_treatment_groups_payload(result)
        )

    def build_patient_id_cross_table_payload(
        self,
        result: PatientIdCrossTableSummaryResult,
    ) -> AnalysisSectionPayload:
        return AnalysisSectionPayload(
            section_title="Podsumowanie powiązań patient_ID między tabelami",
            source_labels=tuple(table.source_label for table in result.tables),
            summary_details=build_patient_id_cross_table_summary_details(result),
            interpretation_summary=build_patient_id_cross_table_interpretation(result),
            table_blocks=(
                ReportTableBlock(
                    title="Unikalne patient_ID w tabelach",
                    columns=("Tabela", "Źródło", "Unikalne patient_ID", "Wykluczone wiersze"),
                    rows=_patient_id_table_count_rows(result),
                ),
                ReportTableBlock(
                    title="Powiązania patient_ID między parami tabel",
                    columns=("Tabela A", "Tabela B", "Wspólne patient_ID", "Tylko w A", "Tylko w B"),
                    rows=_patient_id_pairwise_rows(result),
                ),
                ReportTableBlock(
                    title="Zasięg powiązań",
                    columns=("Metryka", "Wartość"),
                    rows=_patient_id_coverage_rows(result),
                ),
            ),
        )

    def prepare_patient_id_cross_table_report(
        self,
        result: PatientIdCrossTableSummaryResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_patient_id_cross_table_payload(result)
        )

    def export_patient_id_cross_table_report(
        self,
        result: PatientIdCrossTableSummaryResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_patient_id_cross_table_report(result)
        return self.export_section_report(report, destination)

    def export_patient_id_cross_table_report_pdf(
        self,
        result: PatientIdCrossTableSummaryResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_patient_id_cross_table_report(result)
        return self.export_section_report_pdf(report, destination)


    def export_treatment_groups_report(
        self,
        result: TreatmentGroupsResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_treatment_groups_report(result)
        return self.export_section_report(report, destination)

    def export_treatment_groups_report_pdf(
        self,
        result: TreatmentGroupsResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_treatment_groups_report(result)
        return self.export_section_report_pdf(report, destination)


    def export_section_report(
        self,
        report: AnalysisSectionReport,
        destination: Path,
    ) -> str | None:
        try:
            destination.write_text(
                _format_section_report_markdown(report),
                encoding="utf-8",
            )
        except OSError as exc:
            return f"Nie udało się zapisać raportu: {exc}"
        return None

    def export_section_report_pdf(
        self,
        report: AnalysisSectionReport,
        destination: Path,
    ) -> str | None:
        try:
            write_section_report_pdf(report, destination)
        except OSError as exc:
            return f"Nie udało się zapisać raportu PDF: {exc}"
        return None

    def export_diagnosis_frequency_report_pdf(
        self,
        result: DiagnosisFrequencyResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_diagnosis_frequency_report(result)
        return self.export_section_report_pdf(report, destination)


    def export_diagnosis_frequency_report(
        self,
        result: DiagnosisFrequencyResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_diagnosis_frequency_report(result)
        return self.export_section_report(report, destination)

    def prepare_diagnosis_frequency_report(
        self,
        result: DiagnosisFrequencyResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_diagnosis_frequency_payload(result)
        )

    def prepare_combined_automatic_analysis_report(
        self,
    ) -> CombinedAnalysisReport:
        diagnosis_result = DiagnosisFrequencyService().analyze()
        treatment_result = TreatmentGroupsService().analyze()
        patient_id_result = PatientIdCrossTableSummaryService().analyze()
        microbiology_result = MicrobiologyResultsService().analyze()
        diagnosis_culture_result = DiagnosisCultureRelationshipService().analyze()
        procedure_diagnosis_result = ProcedureDiagnosisRelationshipService().analyze()
        treatment_diagnosis_result = TreatmentDiagnosisRelationshipService().analyze()

        return CombinedAnalysisReport(
            report_title="Raport analizy automatycznej",
            generation_context=(
                "Wygenerowano: "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                "Raport łączy siedem modułów analizy automatycznej."
            ),
            sections=(
                self.prepare_diagnosis_frequency_report(diagnosis_result),
                self.prepare_treatment_groups_report(treatment_result),
                self.prepare_patient_id_cross_table_report(patient_id_result),
                self.prepare_microbiology_results_report(microbiology_result),
                self.prepare_diagnosis_culture_relationship_report(diagnosis_culture_result),
                self.prepare_procedure_diagnosis_relationship_report(procedure_diagnosis_result),
                self.prepare_treatment_diagnosis_relationship_report(treatment_diagnosis_result),
            ),
        )

    def export_combined_automatic_analysis_report_pdf(
        self,
        destination: Path,
    ) -> str | None:
        report = self.prepare_combined_automatic_analysis_report()
        try:
            write_combined_analysis_report_pdf(report, destination)
        except OSError as exc:
            return f"Nie udało się zapisać raportu PDF: {exc}"
        return None

def _procedure_diagnosis_relationship_rows(
    result: ProcedureDiagnosisRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.included_cases == 0:
        return ()
    return tuple(
        (
            category.code,
            category.label,
            str(category.clinical_rows),
            format_top_diagnoses(category.top_diagnoses),
        )
        for category in observed_procedure_categories(result)
    )


def _build_procedure_diagnosis_summary_details(
    result: ProcedureDiagnosisRelationshipResult,
) -> str:
    base = build_procedure_diagnosis_summary_details(result)
    if not result.is_success:
        return base

    table_note = build_procedure_diagnosis_table_details(result)
    if not table_note:
        return base
    return f"{base} {table_note}"


def _treatment_diagnosis_relationship_rows(
    result: TreatmentDiagnosisRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.included_cases == 0:
        return ()
    return tuple(
        (
            category.code,
            category.label,
            str(category.clinical_rows),
            format_top_ulcer_categories(category.top_ulcer_categories),
        )
        for category in observed_treatment_categories(result)
    )


def _build_treatment_diagnosis_summary_details(
    result: TreatmentDiagnosisRelationshipResult,
) -> str:
    base = build_treatment_diagnosis_summary_details(result)
    if not result.is_success:
        return base

    table_note = build_treatment_diagnosis_table_details(result)
    if not table_note:
        return base
    return f"{base} {table_note}"


def _diagnosis_culture_category_rows(
    result: DiagnosisCultureRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success:
        return ()
    return tuple(
        (category.code, category.label, str(category.matched_cases))
        for category in result.categories
    )


def _diagnosis_culture_bacteria_rows(
    result: DiagnosisCultureRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.matching.matched_pairs == 0:
        return ()

    rows: list[tuple[str, ...]] = []
    for category in result.categories:
        if category.matched_cases == 0:
            continue
        if not category.bacteria_rows:
            rows.append((category.label, "—", "0"))
            continue
        for bacteria_row in category.bacteria_rows:
            rows.append((category.label, bacteria_row.bacteria, str(bacteria_row.count)))
    return tuple(rows)


def _build_diagnosis_culture_summary_details(result: DiagnosisCultureRelationshipResult) -> str:
    base = build_diagnosis_culture_summary_details(result)
    if not result.is_success:
        return base

    parts = [base, build_diagnosis_culture_matching_details(result)]
    if result.matching.matched_pairs > 0:
        parts.append(
            "Tabela pokazuje izolowane bakterie w dopasowanych przypadkach "
            "dla każdej kategorii type_of_ulcer (x jako other). "
            "Wykluczono puste i xxx."
        )
    return " ".join(parts)



def _microbiology_bacteria_rows(
    result: MicrobiologyResultsResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.matching.matched_pairs == 0:
        return ()
    return tuple(
        (row.bacteria, str(row.count), f"{row.percentage:.1f}")
        for row in result.bacteria_frequencies
    )


def _build_microbiology_results_summary_details(result: MicrobiologyResultsResult) -> str:
    base = build_microbiology_results_summary_details(result)
    if not result.is_success:
        return base

    parts = [base]
    if result.matching.matched_pairs > 0:
        parts.append(
            "Dodatnie izolacje: "
            f"{result.included_isolates}. "
            f"Wyniki negatywne: {result.negative_count} "
            f"({result.negative_percentage:.1f}% ważnych obserwacji bakteryjnych). "
            "W częstotliwości bakterii wykluczono wartości xxx, puste i negative."
        )
    parts.append(build_microbiology_results_matching_details(result))
    return " ".join(parts)



def _build_diagnosis_frequency_summary_details(
    result: DiagnosisFrequencyResult,
) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych clinical."

    return (
        f"Źródło danych: {result.source_label}. "
        f"Przeanalizowano {result.included_cases} z {result.total_cases} przypadków; "
        f"wykluczono {result.excluded_cases} wierszy z pustymi, xxx "
        f"lub nieprawidłowymi kodami type_of_ulcer."
    )




def _patient_id_table_count_rows(
    result: PatientIdCrossTableSummaryResult,
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (
            entry.table_name,
            entry.source_label,
            str(entry.unique_patient_ids),
            str(entry.excluded_rows),
        )
        for entry in result.tables
    )


def _patient_id_pairwise_rows(
    result: PatientIdCrossTableSummaryResult,
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (
            linkage.table_a,
            linkage.table_b,
            str(linkage.shared_count),
            str(linkage.only_in_a),
            str(linkage.only_in_b),
        )
        for linkage in result.pairwise
    )


def _patient_id_coverage_rows(
    result: PatientIdCrossTableSummaryResult,
) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = [
        (
            "patient_ID obecne we wszystkich trzech tabelach",
            str(result.in_all_three),
        )
    ]
    for entry in result.only_in_single_table:
        if entry.count > 0:
            rows.append(
                (
                    f"Identyfikatory wyłącznie w tabeli {entry.table_name}",
                    str(entry.count),
                )
            )
    return tuple(rows)


def _treatment_category_rows(
    rows: tuple[TreatmentCategoryRow, ...],
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (row.code, row.label, str(row.count), f"{row.percentage:.1f}")
        for row in rows
    )


def _ulcer_success_rows(result: TreatmentGroupsResult) -> tuple[tuple[str, ...], ...]:
    ulcer_success = result.ulcer_success
    return (
        ("Przypadki wrzodowe (bez x i xxx)", str(ulcer_success.eligible_cases)),
        ("Wykluczone (how_ended = continuation)", str(ulcer_success.excluded_continuation)),
        ("Ocenione przypadki", str(ulcer_success.evaluated_cases)),
        ("Zakończone jako good", str(ulcer_success.success_count)),
        ("Skuteczność (%)", f"{ulcer_success.success_rate:.1f}"),
    )


def _build_treatment_groups_summary_details(result: TreatmentGroupsResult) -> str:
    base = build_treatment_groups_summary_details(result)
    if not result.is_success:
        return base

    return (
        f"{base} "
        f"farmacology_surgery: {result.pharmacology_included_cases} z {result.total_cases} "
        f"(wykluczono {result.pharmacology_excluded_cases}). "
        f"topical_systemic: {result.topical_included_cases} z {result.total_cases} "
        f"(wykluczono {result.topical_excluded_cases})."
    )


def _format_section_report_markdown(report: AnalysisSectionReport) -> str:
    lines = [
        f"# {report.section_title}",
        "",
        "## Źródła danych",
    ]

    if report.source_labels:
        lines.extend(f"- {label}" for label in report.source_labels)
    else:
        lines.append("- brak")

    lines.extend(
        [
            "",
            "## Podsumowanie",
            report.summary_details or "brak",
            "",
            "## Interpretacja",
            report.interpretation_summary or "brak",
        ]
    )

    for block in report.table_blocks:
        lines.extend(["", f"## {block.title}", ""])
        if not block.columns:
            lines.append("brak kolumn")
            continue

        header = "| " + " | ".join(_escape_markdown_cell(column) for column in block.columns) + " |"
        separator = "| " + " | ".join("---" for _ in block.columns) + " |"
        lines.append(header)
        lines.append(separator)

        if not block.rows:
            empty_row = "| " + " | ".join("" for _ in block.columns) + " |"
            lines.append(empty_row)
            continue

        for row in block.rows:
            padded = list(row) + [""] * (len(block.columns) - len(row))
            lines.append(
                "| "
                + " | ".join(
                    _escape_markdown_cell(str(value))
                    for value in padded[: len(block.columns)]
                )
                + " |"
            )

    lines.append("")
    return "\n".join(lines)


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")
