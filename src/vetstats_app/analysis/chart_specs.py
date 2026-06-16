from __future__ import annotations

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.analysis.diagnosis_culture_relationship import (
    DiagnosisCultureRelationshipResult,
    UlcerCategoryCultureSummary,
    ulcer_relationship_categories,
)
from vetstats_app.analysis.procedure_diagnosis_relationship import (
    ProcedureDiagnosisRelationshipResult,
    format_procedure_code_legend,
    observed_procedure_categories,
)
from vetstats_app.analysis.microbiology_results import MicrobiologyResultsResult
from vetstats_app.analysis.population_characteristics import (
    CategoryCountRow,
    PopulationCharacteristicsResult,
)
from data_sterilizer.schemas.micro import ALLOWED_POSITIVE_SUSCEPTIBILITY
from vetstats_app.analysis.resistance_over_time import (
    SENSITIVITY_CATEGORY_MAPPING,
    ResistanceOverTimeResult,
    YearlyResistanceSummary,
)
from vetstats_app.analysis.treatment_groups import TreatmentCategoryRow, TreatmentGroupsResult
from vetstats_app.analysis.treatment_diagnosis_relationship import (
    TreatmentDiagnosisRelationshipResult,
    observed_treatment_categories,
)


def _yearly_resistance_count(summary: YearlyResistanceSummary, code: str) -> int:
    return next(
        (row.count for row in summary.sensitivity_counts if row.code == code),
        0,
    )


def _category_rows_to_chart(
    *,
    chart_id: str,
    title: str,
    rows: tuple[CategoryCountRow, ...] | tuple[TreatmentCategoryRow, ...],
    x_axis_label: str,
    y_axis_label: str = "Liczba",
) -> AnalysisChartSpec | None:
    observed = [
        row for row in rows if row.count > 0
    ]
    if not observed:
        return None
    return AnalysisChartSpec(
        chart_id=chart_id,
        title=title,
        chart_type="bar",
        labels=tuple(row.label for row in observed),
        values=tuple(float(row.count) for row in observed),
        x_axis_label=x_axis_label,
        y_axis_label=y_axis_label,
    )


def build_population_characteristics_charts(
    result: PopulationCharacteristicsResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success:
        return ()

    charts: list[AnalysisChartSpec] = []

    species_chart = _category_rows_to_chart(
        chart_id="population_species",
        title="Liczba pacjentów według gatunku",
        rows=result.species_counts,
        x_axis_label="Gatunek",
    )
    if species_chart is not None:
        charts.append(species_chart)

    dog_chart = _category_rows_to_chart(
        chart_id="population_dog_breeds",
        title="Liczba psów według rasy",
        rows=result.dog_breed_counts,
        x_axis_label="Rasa",
    )
    if dog_chart is not None:
        charts.append(dog_chart)

    cat_chart = _category_rows_to_chart(
        chart_id="population_cat_breeds",
        title="Liczba kotów według rasy",
        rows=result.cat_breed_counts,
        x_axis_label="Rasa",
    )
    if cat_chart is not None:
        charts.append(cat_chart)

    if len(result.age_years) >= 2:
        charts.append(
            AnalysisChartSpec(
                chart_id="population_age_histogram",
                title="Rozkład wieku pacjentów",
                chart_type="histogram",
                labels=(),
                values=tuple(result.age_years),
                x_axis_label="Wiek (lata)",
                y_axis_label="Liczba pacjentów",
            )
        )

    return tuple(charts)


def build_diagnosis_frequency_charts(
    result: DiagnosisFrequencyResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.included_cases == 0:
        return ()

    observed = [row for row in result.frequencies if row.count > 0]
    if not observed:
        return ()

    return (
        AnalysisChartSpec(
            chart_id="diagnosis_frequency",
            title="Częstość rozpoznań type_of_ulcer",
            chart_type="bar",
            labels=tuple(row.label for row in observed),
            values=tuple(float(row.count) for row in observed),
            x_axis_label="Kategoria type_of_ulcer",
            y_axis_label="Liczba przypadków",
        ),
    )


def build_treatment_groups_charts(
    result: TreatmentGroupsResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success:
        return ()

    charts: list[AnalysisChartSpec] = []

    pharmacology_chart = _category_rows_to_chart(
        chart_id="treatment_pharmacology",
        title="Częstość metod leczenia według farmacology_surgery",
        rows=result.pharmacology_rows,
        x_axis_label="Metoda leczenia",
    )
    if pharmacology_chart is not None:
        charts.append(pharmacology_chart)

    topical_chart = _category_rows_to_chart(
        chart_id="treatment_topical_systemic",
        title="Częstość metod leczenia według topical_systemic",
        rows=result.topical_rows,
        x_axis_label="Metoda leczenia",
    )
    if topical_chart is not None:
        charts.append(topical_chart)

    ulcer_success = result.ulcer_success
    outcome_labels: list[str] = []
    outcome_values: list[float] = []
    if ulcer_success.success_count > 0:
        outcome_labels.append("good")
        outcome_values.append(float(ulcer_success.success_count))
    other_evaluated = ulcer_success.evaluated_cases - ulcer_success.success_count
    if other_evaluated > 0:
        outcome_labels.append("inne ocenione")
        outcome_values.append(float(other_evaluated))
    if ulcer_success.excluded_continuation > 0:
        outcome_labels.append("continuation (wykluczone)")
        outcome_values.append(float(ulcer_success.excluded_continuation))

    if outcome_labels:
        charts.append(
            AnalysisChartSpec(
                chart_id="treatment_outcome",
                title="Częstość wyników leczenia wrzodów (how_ended)",
                chart_type="bar",
                labels=tuple(outcome_labels),
                values=tuple(outcome_values),
                x_axis_label="Wynik leczenia",
                y_axis_label="Liczba przypadków",
            )
        )

    if ulcer_success.evaluated_cases > 0:
        failure_count = ulcer_success.evaluated_cases - ulcer_success.success_count
        if ulcer_success.success_count > 0 or failure_count > 0:
            charts.append(
                AnalysisChartSpec(
                    chart_id="treatment_success",
                    title="Skuteczność leczenia wrzodów",
                    chart_type="bar",
                    labels=("good", "pozostałe ocenione"),
                    values=(
                        float(ulcer_success.success_count),
                        float(failure_count),
                    ),
                    x_axis_label="Wynik",
                    y_axis_label="Liczba przypadków",
                )
            )

    return tuple(charts)


def build_microbiology_results_charts(
    result: MicrobiologyResultsResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.matching.matched_pairs == 0:
        return ()

    labels: list[str] = []
    values: list[float] = []
    for row in result.bacteria_frequencies:
        if row.count <= 0:
            continue
        labels.append(row.bacteria)
        values.append(float(row.count))
    if result.negative_count > 0:
        labels.append("negative")
        values.append(float(result.negative_count))

    if not labels:
        return ()

    return (
        AnalysisChartSpec(
            chart_id="microbiology_results",
            title="Wyniki mikrobiologiczne według kategorii",
            chart_type="bar",
            labels=tuple(labels),
            values=tuple(values),
            x_axis_label="Kategoria wyniku",
            y_axis_label="Liczba obserwacji",
        ),
    )


def build_resistance_over_time_charts(
    result: ResistanceOverTimeResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.exclusions.included_total == 0:
        return ()

    charts: list[AnalysisChartSpec] = []

    year_labels: list[str] = []
    year_values: list[float] = []
    for summary in result.yearly_summaries:
        if summary.included_observations > 0:
            year_labels.append(str(summary.year))
            year_values.append(float(summary.included_observations))
    if year_labels:
        charts.append(
            AnalysisChartSpec(
                chart_id="resistance_observations_by_year",
                title="Liczba obserwacji według roku",
                chart_type="bar",
                labels=tuple(year_labels),
                values=tuple(year_values),
                x_axis_label="Rok",
                y_axis_label="Liczba obserwacji",
            )
        )

    if not result.has_sensitivity_data:
        return tuple(charts)

    resistance_labels: list[str] = []
    resistance_values: list[float] = []
    for summary in result.yearly_summaries:
        resistant = _yearly_resistance_count(summary, "0")
        if summary.included_observations > 0 or resistant > 0:
            resistance_labels.append(str(summary.year))
            resistance_values.append(float(resistant))
    if resistance_labels and any(value > 0 for value in resistance_values):
        charts.append(
            AnalysisChartSpec(
                chart_id="resistance_zero_trend",
                title="Trend oporności (0) według roku",
                chart_type="bar",
                labels=tuple(resistance_labels),
                values=tuple(resistance_values),
                x_axis_label="Rok",
                y_axis_label="Liczba obserwacji oporności (0)",
            )
        )

    category_totals = {
        code: 0 for code, _label in SENSITIVITY_CATEGORY_MAPPING
    }
    for summary in result.yearly_summaries:
        for row in summary.sensitivity_counts:
            category_totals[row.code] += row.count

    mix_labels: list[str] = []
    mix_values: list[float] = []
    for code, label in SENSITIVITY_CATEGORY_MAPPING:
        if code not in ALLOWED_POSITIVE_SUSCEPTIBILITY:
            continue
        count = category_totals[code]
        if count > 0:
            mix_labels.append(code)
            mix_values.append(float(count))
    if mix_labels:
        charts.append(
            AnalysisChartSpec(
                chart_id="resistance_sensitivity_overall",
                title="Rozkład kategorii wrażliwości (+++/+/0)",
                chart_type="bar",
                labels=tuple(mix_labels),
                values=tuple(mix_values),
                x_axis_label="Kategoria wrażliwości",
                y_axis_label="Liczba obserwacji",
            )
        )

    return tuple(charts)


def build_diagnosis_culture_relationship_charts(
    result: DiagnosisCultureRelationshipResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.matching.matched_pairs == 0:
        return ()

    charts: list[AnalysisChartSpec] = []

    observed_categories = [
        category
        for category in ulcer_relationship_categories(result.categories)
        if category.matched_cases > 0
    ]
    if observed_categories:
        charts.append(
            AnalysisChartSpec(
                chart_id="diagnosis_culture_ulcer_distribution",
                title="Rozkład kategorii wrzodu w dopasowanych przypadkach",
                chart_type="bar",
                labels=tuple(category.label for category in observed_categories),
                values=tuple(float(category.matched_cases) for category in observed_categories),
                x_axis_label="Kategoria wrzodu",
                y_axis_label="Liczba przypadków",
            )
        )

    bacteria_totals = _aggregate_bacteria_totals_from_categories(observed_categories)
    if bacteria_totals:
        sorted_bacteria = sorted(
            bacteria_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )
        charts.append(
            AnalysisChartSpec(
                chart_id="diagnosis_culture_bacteria_overall",
                title="Najczęstsze bakterie w dopasowanych posiewach",
                chart_type="bar",
                labels=tuple(name for name, _count in sorted_bacteria),
                values=tuple(float(count) for _name, count in sorted_bacteria),
                x_axis_label="Bakteria",
                y_axis_label="Liczba obserwacji",
                orientation="horizontal",
            )
        )

        pair_rows: list[tuple[str, int]] = []
        for category in observed_categories:
            for bacteria_row in category.bacteria_rows:
                if bacteria_row.count <= 0:
                    continue
                pair_rows.append(
                    (
                        f"{category.label} — {bacteria_row.bacteria}",
                        bacteria_row.count,
                    )
                )
        pair_rows.sort(key=lambda item: (-item[1], item[0]))
        top_pairs = pair_rows[:8]
        if top_pairs:
            charts.append(
                AnalysisChartSpec(
                    chart_id="diagnosis_culture_ulcer_bacteria_pairs",
                    title="Najczęstsze pary kategoria wrzodu — bakteria",
                    chart_type="bar",
                    labels=tuple(label for label, _count in top_pairs),
                    values=tuple(float(count) for _label, count in top_pairs),
                    x_axis_label="Para kategoria — bakteria",
                    y_axis_label="Liczba obserwacji",
                    orientation="horizontal",
                )
            )

    return tuple(charts)


def _aggregate_bacteria_totals_from_categories(
    categories: tuple[UlcerCategoryCultureSummary, ...] | list[UlcerCategoryCultureSummary],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for category in categories:
        for bacteria_row in category.bacteria_rows:
            totals[bacteria_row.bacteria] = (
                totals.get(bacteria_row.bacteria, 0) + bacteria_row.count
            )
    return totals


def build_procedure_diagnosis_relationship_charts(
    result: ProcedureDiagnosisRelationshipResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.included_cases == 0:
        return ()

    charts: list[AnalysisChartSpec] = []

    observed_categories = observed_procedure_categories(result)
    if observed_categories:
        charts.append(
            AnalysisChartSpec(
                chart_id="procedure_diagnosis_surgery_distribution",
                title="Rozkład kategorii zabiegu",
                chart_type="bar",
                labels=tuple(category.label for category in observed_categories),
                values=tuple(float(category.clinical_rows) for category in observed_categories),
                x_axis_label="Kategoria zabiegu",
                y_axis_label="Liczba wierszy",
                legend_note=format_procedure_code_legend(
                    category.code for category in observed_categories
                ),
            )
        )

    if result.included_ulcer_counts:
        charts.append(
            AnalysisChartSpec(
                chart_id="procedure_diagnosis_ulcer_overall",
                title="Najczęstsze rozpoznania ogółem",
                chart_type="bar",
                labels=tuple(row.label for row in result.included_ulcer_counts),
                values=tuple(float(row.count) for row in result.included_ulcer_counts),
                x_axis_label="Rozpoznanie",
                y_axis_label="Liczba wierszy",
                orientation="horizontal",
            )
        )

    if result.procedure_ulcer_pairs:
        top_pairs = result.procedure_ulcer_pairs[:8]
        charts.append(
            AnalysisChartSpec(
                chart_id="procedure_diagnosis_surgery_ulcer_pairs",
                title="Najczęstsze pary zabieg — rozpoznanie",
                chart_type="bar",
                labels=tuple(
                    f"{pair.procedure_label} — {pair.ulcer_label}" for pair in top_pairs
                ),
                values=tuple(float(pair.count) for pair in top_pairs),
                x_axis_label="Para zabieg — rozpoznanie",
                y_axis_label="Liczba wierszy",
                orientation="horizontal",
                legend_note=format_procedure_code_legend(
                    pair.procedure_code for pair in top_pairs
                ),
            )
        )

    return tuple(charts)


def build_treatment_diagnosis_relationship_charts(
    result: TreatmentDiagnosisRelationshipResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.included_cases == 0:
        return ()

    charts: list[AnalysisChartSpec] = []

    observed_categories = observed_treatment_categories(result)
    if observed_categories:
        charts.append(
            AnalysisChartSpec(
                chart_id="treatment_diagnosis_treatment_distribution",
                title="Rozkład kategorii leczenia",
                chart_type="bar",
                labels=tuple(category.label for category in observed_categories),
                values=tuple(float(category.clinical_rows) for category in observed_categories),
                x_axis_label="Rodzaj leczenia",
                y_axis_label="Liczba wierszy",
            )
        )

    if result.included_ulcer_counts:
        charts.append(
            AnalysisChartSpec(
                chart_id="treatment_diagnosis_ulcer_overall",
                title="Najczęstsze typy wrzodu ogółem",
                chart_type="bar",
                labels=tuple(row.label for row in result.included_ulcer_counts),
                values=tuple(float(row.count) for row in result.included_ulcer_counts),
                x_axis_label="Typ wrzodu",
                y_axis_label="Liczba wierszy",
                orientation="horizontal",
            )
        )

    if result.treatment_ulcer_pairs:
        top_pairs = result.treatment_ulcer_pairs[:8]
        charts.append(
            AnalysisChartSpec(
                chart_id="treatment_diagnosis_treatment_ulcer_pairs",
                title="Najczęstsze pary leczenie — typ wrzodu",
                chart_type="bar",
                labels=tuple(
                    f"{pair.treatment_label} — {pair.ulcer_label}" for pair in top_pairs
                ),
                values=tuple(float(pair.count) for pair in top_pairs),
                x_axis_label="Para leczenie — typ wrzodu",
                y_axis_label="Liczba wierszy",
                orientation="horizontal",
            )
        )

    return tuple(charts)
