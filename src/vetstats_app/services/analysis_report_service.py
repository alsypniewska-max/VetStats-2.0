from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from vetstats_app.analysis.chart_specs import (
    build_diagnosis_culture_relationship_charts,
    build_procedure_diagnosis_relationship_charts,
    build_diagnosis_frequency_charts,
    build_microbiology_results_charts,
    build_population_characteristics_charts,
    build_resistance_over_time_charts,
    build_treatment_groups_charts,
    build_treatment_diagnosis_relationship_charts,
    build_duration_of_problem_stats_charts,
    build_micro_monthly_distribution_charts,
    build_pre_swab_drugs_charts,
    build_breed_treatment_duration_charts,
    build_ulcer_breed_treatment_duration_charts,
    build_ems_treatment_duration_charts,
)
from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_CODE_MAPPING,
    DiagnosisFrequencyResult,
    build_descriptive_stats_block as build_diagnosis_frequency_descriptive_stats_block,
    build_interpretation_summary as build_diagnosis_frequency_interpretation,
)
from vetstats_app.analysis.clinical_common import format_optional_number
from vetstats_app.analysis.duration_of_problem_stats import (
    DurationOfProblemStatsResult,
    build_descriptive_stats_block as build_duration_of_problem_descriptive_stats_block,
    build_interpretation_summary as build_duration_of_problem_interpretation,
    build_summary_details as build_duration_of_problem_summary_details,
)
from vetstats_app.analysis.micro_monthly_distribution import (
    MicroMonthlyDistributionResult,
    build_descriptive_stats_block as build_micro_monthly_descriptive_stats_block,
    build_interpretation_summary as build_micro_monthly_interpretation,
    build_summary_details as build_micro_monthly_summary_details,
    monthly_distribution_table_block,
)
from vetstats_app.analysis.breed_treatment_duration import (
    BreedTreatmentDurationResult,
    build_descriptive_stats_block as build_breed_treatment_duration_descriptive_stats_block,
    build_interpretation_summary as build_breed_treatment_duration_interpretation,
    build_summary_details as build_breed_treatment_duration_summary_details,
    cat_breeds_table_block,
    dog_breeds_table_block,
    exclusions_table_block,
    species_summary_table_block,
    statistical_tests_table_block,
)
from vetstats_app.analysis.ulcer_breed_treatment_duration import (
    UlcerBreedTreatmentDurationResult,
    build_descriptive_stats_block as build_ulcer_breed_treatment_duration_descriptive_stats_block,
    build_interpretation_summary as build_ulcer_breed_treatment_duration_interpretation,
    build_summary_details as build_ulcer_breed_treatment_duration_summary_details,
    cat_breed_ulcer_table_block,
    cat_ulcer_types_table_block,
    dog_breed_ulcer_table_block,
    dog_ulcer_types_table_block,
    exclusions_table_block as ulcer_breed_exclusions_table_block,
)
from vetstats_app.analysis.ems_treatment_duration import (
    EmsTreatmentDurationResult,
    build_descriptive_stats_block as build_ems_treatment_duration_descriptive_stats_block,
    build_interpretation_summary as build_ems_treatment_duration_interpretation,
    build_surgery_rate_interpretation_summary as build_ems_surgery_rate_interpretation,
    build_summary_details as build_ems_treatment_duration_summary_details,
    cat_overall_comparison_table_block,
    cat_ulcer_comparison_table_block,
    dog_breed_comparison_table_block,
    dog_overall_comparison_table_block,
    dog_ulcer_comparison_table_block,
    exclusions_table_block as ems_exclusions_table_block,
    overall_comparison_table_block,
    statistical_tests_table_block as ems_statistical_tests_table_block,
    surgery_rate_exclusions_table_block as ems_surgery_rate_exclusions_table_block,
    surgery_rate_summary_table_block as ems_surgery_rate_summary_table_block,
    surgery_rate_ulcer_table_block as ems_surgery_rate_ulcer_table_block,
    ulcer_comparison_table_block,
)
from vetstats_app.analysis.pre_swab_drugs import (
    PreSwabDrugsResult,
    build_descriptive_stats_block as build_pre_swab_drugs_descriptive_stats_block,
    build_interpretation_summary as build_pre_swab_drugs_interpretation,
    build_summary_details as build_pre_swab_drugs_summary_details,
    culture_outcomes_table_block,
    drug_culture_crosstab_table_block,
    top_drugs_table_block,
    treatment_status_culture_crosstab_table_block,
)
from vetstats_app.analysis.treatment_groups import (
    TreatmentCategoryRow,
    TreatmentGroupsResult,
    build_descriptive_stats_block as build_treatment_groups_descriptive_stats_block,
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
    build_descriptive_stats_block as build_diagnosis_culture_descriptive_stats_block,
    build_interpretation_summary as build_diagnosis_culture_interpretation,
    build_matching_details as build_diagnosis_culture_matching_details,
    build_summary_details as build_diagnosis_culture_summary_details,
    ulcer_relationship_categories,
)
from vetstats_app.analysis.procedure_diagnosis_relationship import (
    ProcedureDiagnosisRelationshipResult,
    SECTION_TITLE,
    SUMMARY_RELATIONSHIP_TABLE_COLUMNS,
    build_descriptive_stats_block as build_procedure_diagnosis_descriptive_stats_block,
    build_interpretation_summary as build_procedure_diagnosis_interpretation,
    build_summary_details as build_procedure_diagnosis_summary_details,
    build_table_details as build_procedure_diagnosis_table_details,
    format_top_diagnoses,
    observed_procedure_categories,
    procedure_display_label,
)
from vetstats_app.analysis.treatment_diagnosis_relationship import (
    TreatmentDiagnosisRelationshipResult,
    SECTION_TITLE as TREATMENT_DIAGNOSIS_SECTION_TITLE,
    SUMMARY_RELATIONSHIP_TABLE_COLUMNS as TREATMENT_DIAGNOSIS_SUMMARY_COLUMNS,
    build_descriptive_stats_block as build_treatment_diagnosis_descriptive_stats_block,
    build_interpretation_summary as build_treatment_diagnosis_interpretation,
    build_summary_details as build_treatment_diagnosis_summary_details,
    build_table_details as build_treatment_diagnosis_table_details,
    format_top_ulcer_categories,
    observed_treatment_categories,
    treatment_display_label,
)
from vetstats_app.analysis.microbiology_results import (
    MicrobiologyResultsResult,
    build_descriptive_stats_block as build_microbiology_results_descriptive_stats_block,
    build_interpretation_summary as build_microbiology_results_interpretation,
    build_matching_details as build_microbiology_results_matching_details,
    build_summary_details as build_microbiology_results_summary_details,
)
from vetstats_app.analysis.population_characteristics import (
    PopulationCharacteristicsResult,
    build_interpretation_summary as build_population_characteristics_interpretation,
    build_summary_details as build_population_characteristics_summary_details,
)
from vetstats_app.analysis.resistance_over_time import (
    ResistanceOverTimeResult,
    build_descriptive_stats_block as build_resistance_over_time_descriptive_stats_block,
    build_inclusion_details as build_resistance_over_time_inclusion_details,
    build_interpretation_summary as build_resistance_over_time_interpretation,
    build_summary_details as build_resistance_over_time_summary_details,
)
from datetime import datetime

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv

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
from vetstats_app.services.app_event_logger import log_error, log_info
from vetstats_app.services.section_report_pdf import (
    write_combined_analysis_report_pdf,
    write_section_report_pdf,
)
from vetstats_app.services.microbiology_results_service import MicrobiologyResultsService
from vetstats_app.services.population_characteristics_service import (
    PopulationCharacteristicsService,
)
from vetstats_app.services.procedure_diagnosis_relationship_service import (
    ProcedureDiagnosisRelationshipService,
)
from vetstats_app.services.resistance_over_time_service import ResistanceOverTimeService
from vetstats_app.services.treatment_diagnosis_relationship_service import (
    TreatmentDiagnosisRelationshipService,
)
from vetstats_app.services.treatment_groups_service import TreatmentGroupsService
from vetstats_app.services.duration_of_problem_stats_service import (
    DurationOfProblemStatsService,
)
from vetstats_app.services.micro_monthly_distribution_service import (
    MicroMonthlyDistributionService,
)
from vetstats_app.services.pre_swab_drugs_service import PreSwabDrugsService
from vetstats_app.services.breed_treatment_duration_service import (
    BreedTreatmentDurationService,
)
from vetstats_app.services.ulcer_breed_treatment_duration_service import (
    UlcerBreedTreatmentDurationService,
)
from vetstats_app.services.ems_treatment_duration_service import EmsTreatmentDurationService


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
            chart_specs=payload.chart_specs,
        )

    def build_population_characteristics_payload(
        self,
        result: PopulationCharacteristicsResult,
    ) -> AnalysisSectionPayload:
        table_blocks: tuple[ReportTableBlock, ...] = ()
        if result.is_success:
            table_blocks = (
                ReportTableBlock(
                    title="Podstawowe liczby",
                    columns=("Metryka", "Wartość"),
                    rows=(
                        ("Liczba pacjentów", str(result.total_patients)),
                        ("Liczba rekordów", str(result.total_records)),
                        ("Liczba gatunków", str(result.species_count)),
                    ),
                ),
            )

        return AnalysisSectionPayload(
            section_title="Charakterystyka populacji pacjentów",
            source_labels=(result.source_label,),
            summary_details=build_population_characteristics_summary_details(result),
            interpretation_summary=build_population_characteristics_interpretation(result),
            table_blocks=table_blocks,
            chart_specs=build_population_characteristics_charts(result),
        )

    def prepare_population_characteristics_report(
        self,
        result: PopulationCharacteristicsResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_population_characteristics_payload(result)
        )

    def export_population_characteristics_report_pdf(
        self,
        result: PopulationCharacteristicsResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_population_characteristics_report(result)
        return self.export_section_report_pdf(report, destination)

    def build_diagnosis_frequency_payload(
        self,
        result: DiagnosisFrequencyResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_diagnosis_frequency_descriptive_stats_block(result)
        return AnalysisSectionPayload(
            section_title="Analiza częstości rozpoznań",
            source_labels=(result.source_label,),
            summary_details=_build_diagnosis_frequency_summary_details(result),
            interpretation_summary=build_diagnosis_frequency_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
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
            chart_specs=build_diagnosis_frequency_charts(result),
        )

    def build_treatment_groups_payload(
        self,
        result: TreatmentGroupsResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_treatment_groups_descriptive_stats_block(result)
        return AnalysisSectionPayload(
            section_title="Analiza leczenia w grupach pacjentów",
            source_labels=(result.source_label,),
            summary_details=_build_treatment_groups_summary_details(result),
            interpretation_summary=build_treatment_groups_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
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
            chart_specs=build_treatment_groups_charts(result),
        )

    def build_duration_of_problem_stats_payload(
        self,
        result: DurationOfProblemStatsResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_duration_of_problem_descriptive_stats_block(result)
        return AnalysisSectionPayload(
            section_title="Czas trwania problemu przed pierwszą wizytą",
            source_labels=(result.source_label,),
            summary_details=build_duration_of_problem_summary_details(result),
            interpretation_summary=build_duration_of_problem_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
                ReportTableBlock(
                    title="Czas trwania problemu według typu wrzodu",
                    columns=(
                        "Typ wrzodu",
                        "Liczba",
                        "Średnia (dni)",
                        "Mediana (dni)",
                        "P25 (dni)",
                        "P75 (dni)",
                    ),
                    rows=tuple(
                        (
                            row.ulcer_label,
                            str(row.count),
                            format_optional_number(row.mean_days),
                            format_optional_number(row.median_days),
                            format_optional_number(row.percentile_25_days),
                            format_optional_number(row.percentile_75_days),
                        )
                        for row in result.by_ulcer_type
                    ),
                ),
            ),
            chart_specs=build_duration_of_problem_stats_charts(result),
        )

    def build_micro_monthly_distribution_payload(
        self,
        result: MicroMonthlyDistributionResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_micro_monthly_descriptive_stats_block(result)
        yearly_tables = tuple(
            monthly_distribution_table_block(distribution)
            for distribution in result.yearly_distributions
        )
        combined_table = monthly_distribution_table_block(
            result.combined_distribution,
            combined=True,
        )
        return AnalysisSectionPayload(
            section_title="Rozkład wymazów w miesiącach i latach",
            source_labels=(result.source_label,),
            summary_details=build_micro_monthly_summary_details(result),
            interpretation_summary=build_micro_monthly_interpretation(result),
            table_blocks=(descriptive_stats_block, *yearly_tables, combined_table),
            chart_specs=build_micro_monthly_distribution_charts(result),
        )

    def build_pre_swab_drugs_payload(
        self,
        result: PreSwabDrugsResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_pre_swab_drugs_descriptive_stats_block(result)
        table_blocks = [descriptive_stats_block]
        if result.top_drugs:
            table_blocks.append(top_drugs_table_block(result))
        if result.culture_outcomes:
            table_blocks.append(culture_outcomes_table_block(result))
        if result.treatment_status_culture_crosstab:
            table_blocks.append(treatment_status_culture_crosstab_table_block(result))
        if result.drug_culture_crosstab:
            table_blocks.append(drug_culture_crosstab_table_block(result))
        return AnalysisSectionPayload(
            section_title="Leki stosowane przed wymazem",
            source_labels=(result.source_clinical_label, result.source_micro_label),
            summary_details=build_pre_swab_drugs_summary_details(result),
            interpretation_summary=build_pre_swab_drugs_interpretation(result),
            table_blocks=tuple(table_blocks),
            chart_specs=build_pre_swab_drugs_charts(result),
        )

    def build_breed_treatment_duration_payload(
        self,
        result: BreedTreatmentDurationResult,
    ) -> AnalysisSectionPayload:
        table_blocks = [
            build_breed_treatment_duration_descriptive_stats_block(result),
            exclusions_table_block(result),
        ]
        if result.dog_summary or result.cat_summary:
            table_blocks.append(species_summary_table_block(result))
        if result.dog_breeds:
            table_blocks.append(dog_breeds_table_block(result))
        if result.cat_breeds:
            table_blocks.append(cat_breeds_table_block(result))
        if result.statistical_tests:
            table_blocks.append(statistical_tests_table_block(result))
        return AnalysisSectionPayload(
            section_title="Rasa a czas leczenia",
            source_labels=(result.source_clinical_label, result.source_patient_label),
            summary_details=build_breed_treatment_duration_summary_details(result),
            interpretation_summary=build_breed_treatment_duration_interpretation(result),
            table_blocks=tuple(table_blocks),
            chart_specs=build_breed_treatment_duration_charts(result),
        )

    def build_ulcer_breed_treatment_duration_payload(
        self,
        result: UlcerBreedTreatmentDurationResult,
    ) -> AnalysisSectionPayload:
        table_blocks = [
            build_ulcer_breed_treatment_duration_descriptive_stats_block(result),
            ulcer_breed_exclusions_table_block(result),
        ]
        if result.dog_ulcer_types:
            table_blocks.append(dog_ulcer_types_table_block(result))
        if result.cat_ulcer_types:
            table_blocks.append(cat_ulcer_types_table_block(result))
        if result.dog_breed_ulcer_rows:
            table_blocks.append(dog_breed_ulcer_table_block(result))
        if result.cat_breed_ulcer_rows:
            table_blocks.append(cat_breed_ulcer_table_block(result))
        return AnalysisSectionPayload(
            section_title="Typ wrzodu a czas leczenia w obrębie ras",
            source_labels=(result.source_clinical_label, result.source_patient_label),
            summary_details=build_ulcer_breed_treatment_duration_summary_details(result),
            interpretation_summary=build_ulcer_breed_treatment_duration_interpretation(
                result
            ),
            table_blocks=tuple(table_blocks),
            chart_specs=build_ulcer_breed_treatment_duration_charts(result),
        )

    def build_ems_treatment_duration_payload(
        self,
        result: EmsTreatmentDurationResult,
    ) -> AnalysisSectionPayload:
        table_blocks = [
            build_ems_treatment_duration_descriptive_stats_block(result),
            ems_exclusions_table_block(result),
        ]
        overall_block = overall_comparison_table_block(result)
        if overall_block.rows:
            table_blocks.append(overall_block)
        ulcer_block = ulcer_comparison_table_block(result)
        if ulcer_block.rows:
            table_blocks.append(ulcer_block)
        dog_overall_block = dog_overall_comparison_table_block(result)
        if dog_overall_block.rows:
            table_blocks.append(dog_overall_block)
        dog_ulcer_block = dog_ulcer_comparison_table_block(result)
        if dog_ulcer_block.rows:
            table_blocks.append(dog_ulcer_block)
        cat_overall_block = cat_overall_comparison_table_block(result)
        if cat_overall_block.rows:
            table_blocks.append(cat_overall_block)
        cat_ulcer_block = cat_ulcer_comparison_table_block(result)
        if cat_ulcer_block.rows:
            table_blocks.append(cat_ulcer_block)
        dog_breed_block = dog_breed_comparison_table_block(result)
        if dog_breed_block.rows:
            table_blocks.append(dog_breed_block)
        if result.statistical_tests:
            table_blocks.append(ems_statistical_tests_table_block(result))
        table_blocks.append(ems_surgery_rate_exclusions_table_block(result))
        surgery_summary_block = ems_surgery_rate_summary_table_block(result)
        if surgery_summary_block.rows:
            table_blocks.append(surgery_summary_block)
        surgery_ulcer_block = ems_surgery_rate_ulcer_table_block(result)
        if surgery_ulcer_block.rows:
            table_blocks.append(surgery_ulcer_block)
        ems_interpretation = build_ems_treatment_duration_interpretation(result)
        surgery_interpretation = build_ems_surgery_rate_interpretation(result)
        interpretation_parts = [ems_interpretation]
        if surgery_interpretation:
            interpretation_parts.append(surgery_interpretation)
        return AnalysisSectionPayload(
            section_title="Stosowanie EMS a czas leczenia",
            source_labels=(result.source_clinical_label, result.source_patient_label),
            summary_details=build_ems_treatment_duration_summary_details(result),
            interpretation_summary="\n\n".join(interpretation_parts),
            table_blocks=tuple(table_blocks),
            chart_specs=build_ems_treatment_duration_charts(result),
        )

    def build_microbiology_results_payload(
        self,
        result: MicrobiologyResultsResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_microbiology_results_descriptive_stats_block(result)
        return AnalysisSectionPayload(
            section_title="Analiza wyników mikrobiologicznych",
            source_labels=(
                result.source_clinical_label,
                result.source_micro_label,
            ),
            summary_details=_build_microbiology_results_summary_details(result),
            interpretation_summary=build_microbiology_results_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
                ReportTableBlock(
                    title="Najczęściej izolowane bakterie i wyniki negatywne",
                    columns=("Bakteria", "Liczba", "Udział (%)"),
                    rows=_microbiology_bacteria_rows(result),
                ),
            ),
            chart_specs=build_microbiology_results_charts(result),
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

    def build_resistance_over_time_payload(
        self,
        result: ResistanceOverTimeResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_resistance_over_time_descriptive_stats_block(result)
        table_blocks: list[ReportTableBlock] = [
            descriptive_stats_block,
            ReportTableBlock(
                title="Zakres czasowy analizy",
                columns=("Rok", "Obserwacje", "Najczęstsza bakteria", "Liczba"),
                rows=_resistance_yearly_overview_rows(result),
            ),
        ]
        sensitivity_rows = _resistance_sensitivity_rows(result)
        if sensitivity_rows:
            table_blocks.append(
                ReportTableBlock(
                    title="Ogólne podsumowanie wrażliwości rocznej",
                    columns=("Rok", "+++", "+", "0"),
                    rows=sensitivity_rows,
                )
            )

        return AnalysisSectionPayload(
            section_title="Analiza oporności bakterii w czasie",
            source_labels=(result.source_label,),
            summary_details=_build_resistance_over_time_summary_details(result),
            interpretation_summary=build_resistance_over_time_interpretation(result),
            table_blocks=tuple(table_blocks),
            chart_specs=build_resistance_over_time_charts(result),
        )

    def prepare_resistance_over_time_report(
        self,
        result: ResistanceOverTimeResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_resistance_over_time_payload(result)
        )

    def export_resistance_over_time_report_pdf(
        self,
        result: ResistanceOverTimeResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_resistance_over_time_report(result)
        return self.export_section_report_pdf(report, destination)

    def build_diagnosis_culture_relationship_payload(
        self,
        result: DiagnosisCultureRelationshipResult,
    ) -> AnalysisSectionPayload:
        descriptive_stats_block = build_diagnosis_culture_descriptive_stats_block(result)
        return AnalysisSectionPayload(
            section_title="Powiązanie rozpoznań z wynikami posiewu",
            source_labels=(
                result.source_clinical_label,
                result.source_micro_label,
            ),
            summary_details=_build_diagnosis_culture_summary_details(result),
            interpretation_summary=build_diagnosis_culture_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
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
            chart_specs=build_diagnosis_culture_relationship_charts(result),
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
        descriptive_stats_block = build_procedure_diagnosis_descriptive_stats_block(result)
        return AnalysisSectionPayload(
            section_title=SECTION_TITLE,
            source_labels=(result.source_label,),
            summary_details=_build_procedure_diagnosis_summary_details(result),
            interpretation_summary=build_procedure_diagnosis_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
                ReportTableBlock(
                    title=SECTION_TITLE,
                    columns=SUMMARY_RELATIONSHIP_TABLE_COLUMNS,
                    rows=_procedure_diagnosis_relationship_rows(result),
                ),
                ReportTableBlock(
                    title="Szczegółowe pary zabieg — rozpoznanie",
                    columns=("Kategoria zabiegu", "Rozpoznanie", "Liczba wierszy"),
                    rows=_procedure_diagnosis_pair_rows(result),
                ),
            ),
            chart_specs=build_procedure_diagnosis_relationship_charts(result),
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
        descriptive_stats_block = build_treatment_diagnosis_descriptive_stats_block(
            result
        )
        return AnalysisSectionPayload(
            section_title=TREATMENT_DIAGNOSIS_SECTION_TITLE,
            source_labels=(result.source_label,),
            summary_details=_build_treatment_diagnosis_summary_details(result),
            interpretation_summary=build_treatment_diagnosis_interpretation(result),
            table_blocks=(
                descriptive_stats_block,
                ReportTableBlock(
                    title=TREATMENT_DIAGNOSIS_SECTION_TITLE,
                    columns=TREATMENT_DIAGNOSIS_SUMMARY_COLUMNS,
                    rows=_treatment_diagnosis_relationship_rows(result),
                ),
                ReportTableBlock(
                    title="Szczegółowe pary leczenie — typ wrzodu",
                    columns=(
                        "Rodzaj leczenia",
                        "Typ wrzodu",
                        "Liczba wierszy",
                        "Udział w typie wrzodu (%)",
                    ),
                    rows=_treatment_diagnosis_pair_rows(result),
                ),
            ),
            chart_specs=build_treatment_diagnosis_relationship_charts(result),
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
            message = f"Nie udało się zapisać raportu PDF: {exc}"
            log_error(
                "analysis_report",
                f"Eksport raportu PDF {report.section_title} nie powiódł się: {exc}",
            )
            return message
        log_info(
            "analysis_report",
            (
                f"Wyeksportowano raport PDF: {report.section_title} → "
                f"{Path(destination).name}"
            ),
        )
        return None

    def export_diagnosis_frequency_report_pdf(
        self,
        result: DiagnosisFrequencyResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_diagnosis_frequency_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_duration_of_problem_stats_report(
        self,
        result: DurationOfProblemStatsResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_duration_of_problem_stats_payload(result)
        )

    def export_duration_of_problem_stats_report_pdf(
        self,
        result: DurationOfProblemStatsResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_duration_of_problem_stats_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_micro_monthly_distribution_report(
        self,
        result: MicroMonthlyDistributionResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_micro_monthly_distribution_payload(result)
        )

    def export_micro_monthly_distribution_report_pdf(
        self,
        result: MicroMonthlyDistributionResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_micro_monthly_distribution_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_pre_swab_drugs_report(
        self,
        result: PreSwabDrugsResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_pre_swab_drugs_payload(result)
        )

    def export_pre_swab_drugs_report_pdf(
        self,
        result: PreSwabDrugsResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_pre_swab_drugs_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_breed_treatment_duration_report(
        self,
        result: BreedTreatmentDurationResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_breed_treatment_duration_payload(result)
        )

    def export_breed_treatment_duration_report_pdf(
        self,
        result: BreedTreatmentDurationResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_breed_treatment_duration_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_ulcer_breed_treatment_duration_report(
        self,
        result: UlcerBreedTreatmentDurationResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_ulcer_breed_treatment_duration_payload(result)
        )

    def export_ulcer_breed_treatment_duration_report_pdf(
        self,
        result: UlcerBreedTreatmentDurationResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_ulcer_breed_treatment_duration_report(result)
        return self.export_section_report_pdf(report, destination)

    def prepare_ems_treatment_duration_report(
        self,
        result: EmsTreatmentDurationResult,
    ) -> AnalysisSectionReport:
        return self.build_section_report(
            self.build_ems_treatment_duration_payload(result)
        )

    def export_ems_treatment_duration_report_pdf(
        self,
        result: EmsTreatmentDurationResult,
        destination: Path,
    ) -> str | None:
        report = self.prepare_ems_treatment_duration_report(result)
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
        *,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> tuple[CombinedAnalysisReport, tuple[tuple[str, str], ...]]:
        section_specs: tuple[tuple[str, Callable[[], AnalysisSectionReport]], ...] = (
            (
                "Charakterystyka populacji pacjentów",
                lambda: self.prepare_population_characteristics_report(
                    PopulationCharacteristicsService().analyze()
                ),
            ),
            (
                "Analiza częstości rozpoznań",
                lambda: self.prepare_diagnosis_frequency_report(
                    DiagnosisFrequencyService().analyze()
                ),
            ),
            (
                "Analiza leczenia w grupach pacjentów",
                lambda: self.prepare_treatment_groups_report(
                    TreatmentGroupsService().analyze()
                ),
            ),
            (
                "Analiza wyników mikrobiologicznych",
                lambda: self.prepare_microbiology_results_report(
                    MicrobiologyResultsService().analyze()
                ),
            ),
            (
                "Analiza oporności bakterii w czasie",
                lambda: self.prepare_resistance_over_time_report(
                    ResistanceOverTimeService().analyze()
                ),
            ),
            (
                "Powiązanie rozpoznań z posiewem",
                lambda: self.prepare_diagnosis_culture_relationship_report(
                    DiagnosisCultureRelationshipService().analyze()
                ),
            ),
            (
                "Analiza zależności między zabiegiem a rozpoznaniem",
                lambda: self.prepare_procedure_diagnosis_relationship_report(
                    ProcedureDiagnosisRelationshipService().analyze()
                ),
            ),
            (
                "Powiązanie leczenia z typem wrzodu",
                lambda: self.prepare_treatment_diagnosis_relationship_report(
                    TreatmentDiagnosisRelationshipService().analyze()
                ),
            ),
            (
                "Rasa a czas leczenia",
                lambda: self.prepare_breed_treatment_duration_report(
                    BreedTreatmentDurationService().analyze()
                ),
            ),
            (
                "Typ wrzodu a czas leczenia w obrębie ras",
                lambda: self.prepare_ulcer_breed_treatment_duration_report(
                    UlcerBreedTreatmentDurationService().analyze()
                ),
            ),
            (
                "Stosowanie EMS a czas leczenia",
                lambda: self.prepare_ems_treatment_duration_report(
                    EmsTreatmentDurationService().analyze()
                ),
            ),
            (
                "Czas trwania problemu przed pierwszą wizytą",
                lambda: self.prepare_duration_of_problem_stats_report(
                    DurationOfProblemStatsService().analyze()
                ),
            ),
            (
                "Rozkład wymazów w miesiącach i latach",
                lambda: self.prepare_micro_monthly_distribution_report(
                    MicroMonthlyDistributionService().analyze()
                ),
            ),
            (
                "Leki stosowane przed wymazem",
                lambda: self.prepare_pre_swab_drugs_report(
                    PreSwabDrugsService().analyze()
                ),
            ),
            (
                "Powiązania patient_ID między tabelami",
                lambda: self.prepare_patient_id_cross_table_report(
                    PatientIdCrossTableSummaryService().analyze()
                ),
            ),
        )

        sections: list[AnalysisSectionReport] = []
        section_errors: list[tuple[str, str]] = []
        total = len(section_specs)

        for index, (section_title, builder) in enumerate(section_specs, start=1):
            if progress_callback is not None:
                progress_callback(section_title, index, total)
            try:
                sections.append(builder())
            except Exception as exc:
                message = str(exc).strip() or exc.__class__.__name__
                section_errors.append((section_title, message))
                sections.append(_build_failed_section_report(section_title, message))
                log_error(
                    "analysis_report",
                    f"Sekcja raportu {section_title} nie powiodła się: {message}",
                )

        sections_tuple = tuple(sections)

        return (
            CombinedAnalysisReport(
                report_title="Raport analizy automatycznej",
                generation_context=(
                    "Wygenerowano: "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                    f"Raport łączy {len(section_specs)} modułów analizy automatycznej."
                ),
                sections=sections_tuple,
                source_data_description=_build_combined_source_data_description(
                    sections_tuple
                ),
                applied_filters=_build_combined_applied_filters(),
                dataset_dimensions=_build_combined_dataset_dimensions(),
                verbal_analysis_summary=_build_combined_verbal_analysis_summary(
                    sections_tuple
                ),
                section_overview_rows=_build_combined_section_overview_rows(
                    sections_tuple
                ),
            ),
            tuple(section_errors),
        )

    def prepare_final_automatic_analysis_report(
        self,
    ) -> CombinedAnalysisReport:
        report, _errors = self.prepare_combined_automatic_analysis_report()
        return report

    def export_combined_automatic_analysis_report_pdf(
        self,
        destination: Path,
        *,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> str | None:
        report, _errors = self.prepare_combined_automatic_analysis_report(
            progress_callback=progress_callback,
        )
        try:
            write_combined_analysis_report_pdf(report, destination)
        except OSError as exc:
            message = f"Nie udało się zapisać raportu PDF: {exc}"
            log_error(
                "analysis_report",
                (
                    f"Eksport raportu PDF {report.report_title} nie powiódł się: "
                    f"{exc}"
                ),
            )
            return message
        log_info(
            "analysis_report",
            (
                f"Wyeksportowano raport PDF: {report.report_title} → "
                f"{Path(destination).name}"
            ),
        )
        return None

    def export_final_automatic_analysis_report_pdf(
        self,
        destination: Path,
    ) -> str | None:
        return self.export_combined_automatic_analysis_report_pdf(destination)


def _resolve_dataset_path(dataset_name: str) -> Path | None:
    candidates = (
        DEFAULT_OUTPUT_DIR / sterile_output_name(dataset_name),
        DEFAULT_INPUT_DIR / dataset_name,
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def resolve_dataset_label() -> str:
    parts: list[str] = []
    for dataset_name in ("patient.csv", "clinical.csv", "micro.csv"):
        path = _resolve_dataset_path(dataset_name)
        if path is not None:
            parts.append(f"{dataset_name} ({path.parent.name}/{path.name})")
    if not parts:
        return "Brak zidentyfikowanych plików źródłowych."
    return "; ".join(parts)


def _build_failed_section_report(
    section_title: str,
    error_message: str,
) -> AnalysisSectionReport:
    return AnalysisSectionReport(
        section_title=section_title,
        source_labels=(),
        summary_details=f"Nie udało się wygenerować tej sekcji: {error_message}",
        interpretation_summary="",
        table_blocks=(),
        chart_specs=(),
    )


def _build_combined_source_data_description(
    sections: tuple[AnalysisSectionReport, ...],
) -> str:
    labels: list[str] = []
    for section in sections:
        for label in section.source_labels:
            if label not in labels:
                labels.append(label)

    if not labels:
        return "Brak zidentyfikowanych plików źródłowych."

    dataset_paths = []
    for dataset_name in ("patient.csv", "clinical.csv", "micro.csv"):
        path = _resolve_dataset_path(dataset_name)
        if path is not None:
            dataset_paths.append(f"{dataset_name} → {path.name}")

    parts = [
        "Raport korzysta z wyników modułów analizy automatycznej na danych "
        "wstępnie oczyszczonych (Sterile_data lub Data_to_check).",
        f"Wykorzystane etykiety źródeł w sekcjach: {', '.join(labels)}.",
    ]
    if dataset_paths:
        parts.append(f"Mapowanie tabel: {'; '.join(dataset_paths)}.")
    return " ".join(parts)


def _build_combined_applied_filters() -> str:
    return (
        "Filtry są stosowane przez istniejące moduły analizy — raport końcowy "
        "nie wprowadza dodatkowych reguł. Wspólne wykluczenia obejmują: wartości "
        "puste i xxx, nieprawidłowe kody pól klinicznych (type_of_ulcer, "
        "topical_systemic, type_of_surgery, pharmacology_surgery), nieprawidłowe "
        "patient_ID oraz w modułach łączących clinical z micro — wiersze bez "
        "dopasowanej pary patient_ID. Szczegóły wykluczeń dla każdego modułu "
        "znajdują się w podsumowaniu danej sekcji."
    )


def _build_combined_dataset_dimensions() -> str:
    parts: list[str] = []
    for dataset_name in ("patient.csv", "clinical.csv", "micro.csv"):
        path = _resolve_dataset_path(dataset_name)
        if path is None:
            parts.append(f"{dataset_name}: brak pliku.")
            continue
        frame = load_csv(path)
        parts.append(
            f"{path.name}: {len(frame)} wierszy, {len(frame.columns)} kolumn "
            f"({', '.join(str(column) for column in frame.columns)})."
        )
    return " ".join(parts)


def _build_combined_verbal_analysis_summary(
    sections: tuple[AnalysisSectionReport, ...],
) -> str:
    if not sections:
        return "Brak sekcji do podsumowania."

    parts = [
        "Poniżej skrót interpretacji poszczególnych modułów wchodzących w skład "
        "raportu końcowego. Pełne tabele i opisy znajdują się w kolejnych sekcjach."
    ]
    for section in sections:
        interpretation = section.interpretation_summary.strip()
        if interpretation:
            parts.append(f"{section.section_title}: {interpretation}")
        else:
            parts.append(f"{section.section_title}: brak interpretacji.")
    return " ".join(parts)


def _build_combined_section_overview_rows(
    sections: tuple[AnalysisSectionReport, ...],
) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (
            section.section_title,
            str(section.table_count),
            str(section.row_count),
        )
        for section in sections
    )


def _procedure_diagnosis_relationship_rows(
    result: ProcedureDiagnosisRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.included_cases == 0:
        return ()
    return tuple(
        (
            category.code,
            procedure_display_label(category.code),
            str(category.clinical_rows),
            format_top_diagnoses(category.top_diagnoses),
        )
        for category in observed_procedure_categories(result)
    )


def _procedure_diagnosis_pair_rows(
    result: ProcedureDiagnosisRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.included_cases == 0:
        return ()
    return tuple(
        (pair.procedure_label, pair.ulcer_label, str(pair.count))
        for pair in result.procedure_ulcer_pairs
        if pair.count > 0
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
            treatment_display_label(category.code),
            str(category.clinical_rows),
            format_top_ulcer_categories(category.top_ulcer_categories),
        )
        for category in observed_treatment_categories(result)
    )


def _treatment_diagnosis_pair_rows(
    result: TreatmentDiagnosisRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.included_cases == 0:
        return ()
    return tuple(
        (
            pair.treatment_label,
            pair.ulcer_label,
            str(pair.count),
            f"{pair.ulcer_type_share_pct:.1f}",
        )
        for pair in result.treatment_ulcer_pairs
        if pair.count > 0
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
        for category in ulcer_relationship_categories(result.categories)
    )


def _diagnosis_culture_bacteria_rows(
    result: DiagnosisCultureRelationshipResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or result.matching.matched_pairs == 0:
        return ()

    rows: list[tuple[str, ...]] = []
    for category in ulcer_relationship_categories(result.categories):
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
            "dla każdej kategorii type_of_ulcer (x jako other (non ulcer)). "
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


def _resistance_yearly_overview_rows(
    result: ResistanceOverTimeResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success:
        return ()
    return tuple(
        (
            str(summary.year),
            str(summary.included_observations),
            summary.most_common_bacteria or "—",
            str(summary.most_common_bacteria_count),
        )
        for summary in result.yearly_summaries
    )


def _resistance_sensitivity_rows(
    result: ResistanceOverTimeResult,
) -> tuple[tuple[str, ...], ...]:
    if not result.is_success or not result.has_sensitivity_data:
        return ()
    return tuple(
        (
            str(summary.year),
            str(next((row.count for row in summary.sensitivity_counts if row.code == "+++"), 0)),
            str(next((row.count for row in summary.sensitivity_counts if row.code == "+"), 0)),
            str(next((row.count for row in summary.sensitivity_counts if row.code == "0"), 0)),
        )
        for summary in result.yearly_summaries
    )


def _build_resistance_over_time_summary_details(
    result: ResistanceOverTimeResult,
) -> str:
    base = build_resistance_over_time_summary_details(result)
    if not result.is_success:
        return base

    return f"{base} {build_resistance_over_time_inclusion_details(result)}"



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
