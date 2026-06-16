from __future__ import annotations

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.analysis.diagnosis_frequency import DiagnosisFrequencyResult
from vetstats_app.analysis.microbiology_results import MicrobiologyResultsResult
from vetstats_app.analysis.population_characteristics import (
    CategoryCountRow,
    PopulationCharacteristicsResult,
)
from vetstats_app.analysis.treatment_groups import TreatmentCategoryRow, TreatmentGroupsResult


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
