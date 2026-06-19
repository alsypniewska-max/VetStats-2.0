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
    resistance_relevant_sensitivity_total,
)
from vetstats_app.analysis.treatment_groups import TreatmentCategoryRow, TreatmentGroupsResult
from vetstats_app.analysis.treatment_diagnosis_relationship import (
    TreatmentDiagnosisRelationshipResult,
    observed_treatment_categories,
)
from vetstats_app.analysis.duration_of_problem_stats import DurationOfProblemStatsResult
from vetstats_app.analysis.micro_monthly_distribution import (
    MicroMonthlyDistributionResult,
    YearlyMonthlyDistribution,
)
from vetstats_app.analysis.pre_swab_drugs import (
    CULTURE_OUTCOME_ORDER,
    NO_PRIOR_TREATMENT_LABEL,
    PreSwabDrugsResult,
    TREATMENT_STATUS_ORDER,
)
from vetstats_app.analysis.breed_treatment_duration import BreedTreatmentDurationResult
from vetstats_app.analysis.ulcer_breed_treatment_duration import (
    UlcerBreedTreatmentDurationResult,
)
from vetstats_app.analysis.ems_treatment_duration import EmsTreatmentDurationResult


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
        valid_observations = resistance_relevant_sensitivity_total(summary)
        if valid_observations <= 0:
            continue
        resistant = _yearly_resistance_count(summary, "0")
        resistance_rate = resistant / valid_observations * 100.0
        resistance_labels.append(str(summary.year))
        resistance_values.append(resistance_rate)
    if resistance_labels:
        charts.append(
            AnalysisChartSpec(
                chart_id="resistance_zero_trend",
                title="Trend oporności według roku",
                chart_type="bar",
                labels=tuple(resistance_labels),
                values=tuple(resistance_values),
                x_axis_label="Rok",
                y_axis_label="Odsetek oporności (0) [%]",
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


def build_duration_of_problem_stats_charts(
    result: DurationOfProblemStatsResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.included_rows == 0:
        return ()

    observed = [
        row
        for row in result.by_ulcer_type
        if row.count > 0 and row.median_days is not None and row.mean_days is not None
    ]
    if not observed:
        return ()

    ulcer_labels = tuple(row.ulcer_label for row in observed)
    charts: list[AnalysisChartSpec] = [
        AnalysisChartSpec(
            chart_id="duration_of_problem_by_ulcer",
            title="Mediana czasu trwania problemu przed wizytą według typu wrzodu",
            subtitle="Wartość medianowa (mediana) w dniach",
            chart_type="bar",
            labels=ulcer_labels,
            values=tuple(float(row.median_days) for row in observed),
            x_axis_label="Typ wrzodu",
            y_axis_label="Mediana (dni)",
        ),
        AnalysisChartSpec(
            chart_id="duration_of_problem_mean_by_ulcer",
            title="Średnia czasu trwania problemu przed wizytą według typu wrzodu",
            subtitle="Wartość średnia (mean) w dniach",
            chart_type="bar",
            labels=ulcer_labels,
            values=tuple(float(row.mean_days) for row in observed),
            x_axis_label="Typ wrzodu",
            y_axis_label="Średnia (dni)",
        ),
        AnalysisChartSpec(
            chart_id="duration_of_problem_mean_vs_median_by_ulcer",
            title="Porównanie średniej i mediany czasu trwania problemu",
            subtitle="Średnia vs mediana według typu wrzodu (dni)",
            chart_type="grouped_bar",
            labels=ulcer_labels,
            values=tuple(float(row.mean_days) for row in observed),
            secondary_values=tuple(float(row.median_days) for row in observed),
            x_axis_label="Typ wrzodu",
            y_axis_label="Czas trwania (dni)",
        ),
    ]

    if len(result.all_duration_days) >= 2:
        charts.append(
            AnalysisChartSpec(
                chart_id="duration_of_problem_histogram",
                title="Rozkład czasu trwania problemu przed wizytą",
                subtitle="Histogram łączny dla wszystkich uwzględnionych przypadków wrzodowych",
                chart_type="histogram",
                labels=(),
                values=result.all_duration_days,
                x_axis_label="Czas trwania (dni)",
                y_axis_label="Liczba przypadków",
            )
        )

    box_groups = tuple(
        group.duration_days
        for group in result.duration_value_groups
        if group.duration_days
    )
    box_labels = tuple(
        group.ulcer_label
        for group in result.duration_value_groups
        if group.duration_days
    )
    if box_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="duration_of_problem_box_by_ulcer",
                title="Rozstęp i wartości odstające czasu trwania problemu",
                subtitle="Wykres pudełkowy (box plot) według typu wrzodu — mediana, kwartyle i outliery",
                chart_type="box",
                labels=box_labels,
                values=(),
                box_plot_groups=box_groups,
                x_axis_label="Typ wrzodu",
                y_axis_label="Czas trwania (dni)",
            )
        )

    if result.all_duration_days:
        thresholds = (7, 14, 30, 90)
        total = len(result.all_duration_days)
        charts.append(
            AnalysisChartSpec(
                chart_id="duration_of_problem_cumulative",
                title="Skumulowany udział przypadków według czasu trwania problemu",
                subtitle="Odsetek przypadków z czasem trwania nie dłuższym niż podany próg",
                chart_type="bar",
                labels=tuple(f"≤{threshold} dni" for threshold in thresholds),
                values=tuple(
                    sum(1 for value in result.all_duration_days if value <= threshold)
                    / total
                    * 100.0
                    for threshold in thresholds
                ),
                x_axis_label="Próg czasu trwania",
                y_axis_label="Udział przypadków (%)",
            )
        )

    return tuple(charts)


def _monthly_distribution_chart(
    *,
    chart_id: str,
    title: str,
    distribution: YearlyMonthlyDistribution,
) -> AnalysisChartSpec:
    return AnalysisChartSpec(
        chart_id=chart_id,
        title=title,
        chart_type="bar",
        labels=tuple(row.month_label for row in distribution.months),
        values=tuple(float(row.count) for row in distribution.months),
        x_axis_label="Miesiąc",
        y_axis_label="Liczba wymazów",
    )


def build_micro_monthly_distribution_charts(
    result: MicroMonthlyDistributionResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.included_swabs == 0:
        return ()

    charts: list[AnalysisChartSpec] = []
    for distribution in result.yearly_distributions:
        charts.append(
            _monthly_distribution_chart(
                chart_id=f"micro_monthly_{distribution.year}",
                title=f"Rozkład wymazów według miesiąca — {distribution.year}",
                distribution=distribution,
            )
        )
    charts.append(
        _monthly_distribution_chart(
            chart_id="micro_monthly_combined",
            title="Rozkład wymazów według miesiąca — wszystkie lata",
            distribution=result.combined_distribution,
        )
    )
    return tuple(charts)


def _culture_counts_for_drug(
    result: PreSwabDrugsResult,
    drug_label: str,
) -> tuple[tuple[str, float], ...]:
    rows = [
        row
        for row in result.drug_culture_crosstab
        if row.drug_label == drug_label and row.count > 0
    ]
    rows.sort(key=lambda row: (-row.count, row.culture_outcome))
    return tuple((row.culture_outcome, float(row.count)) for row in rows)


def _treatment_status_stacked_series(
    result: PreSwabDrugsResult,
) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    counts: dict[tuple[str, str], int] = {
        (row.treatment_status_label, row.culture_outcome): row.count
        for row in result.treatment_status_culture_crosstab
    }
    series_values: list[tuple[float, ...]] = []
    present_outcomes: list[str] = []
    for culture_outcome in CULTURE_OUTCOME_ORDER:
        values = tuple(
            float(counts.get((treatment_status, culture_outcome), 0))
            for treatment_status in TREATMENT_STATUS_ORDER
        )
        if any(value > 0 for value in values):
            present_outcomes.append(culture_outcome)
            series_values.append(values)
    return tuple(present_outcomes), tuple(series_values)


def build_pre_swab_drugs_charts(
    result: PreSwabDrugsResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success or result.total_clinical_rows == 0:
        return ()

    charts: list[AnalysisChartSpec] = []

    if result.top_drugs:
        top_rows = result.top_drugs[:8]
        charts.append(
            AnalysisChartSpec(
                chart_id="pre_swab_top_drugs",
                title="Najczęściej stosowane leki przed wymazem",
                subtitle="Liczba wystąpień znormalizowanych nazw leków",
                chart_type="bar",
                labels=tuple(row.drug_label for row in top_rows),
                values=tuple(float(row.count) for row in top_rows),
                x_axis_label="Lek",
                y_axis_label="Liczba wystąpień",
            )
        )

    treatment_buckets = (
        ("Brak leczenia (x)", float(result.no_prior_treatment_count)),
        ("Nieznany wpis leku", float(result.unknown_drug_count)),
        ("Podano lek", float(result.with_known_drugs_count)),
    )
    if any(value > 0 for _, value in treatment_buckets):
        charts.append(
            AnalysisChartSpec(
                chart_id="pre_swab_treatment_buckets",
                title="Status leczenia przed wymazem",
                subtitle="Podział wierszy clinical według pola drug_used_before_micro",
                chart_type="bar",
                labels=tuple(label for label, _ in treatment_buckets),
                values=tuple(value for _, value in treatment_buckets),
                x_axis_label="Kategoria",
                y_axis_label="Liczba przypadków",
            )
        )

    if result.culture_outcomes:
        charts.append(
            AnalysisChartSpec(
                chart_id="pre_swab_culture_outcomes",
                title="Wyniki posiewu w dopasowanych przypadkach",
                subtitle="Klasyfikacja wyniku mikrobiologicznego po dopasowaniu clinical–micro",
                chart_type="bar",
                labels=tuple(row.outcome_label for row in result.culture_outcomes),
                values=tuple(float(row.count) for row in result.culture_outcomes),
                x_axis_label="Wynik posiewu",
                y_axis_label="Liczba przypadków",
            )
        )

    if result.top_drugs and result.drug_culture_crosstab:
        top_drug = result.top_drugs[0].drug_label
        culture_counts = _culture_counts_for_drug(result, top_drug)
        if culture_counts:
            charts.append(
                AnalysisChartSpec(
                    chart_id="pre_swab_top_drug_culture",
                    title=f"Wynik posiewu a lek przed wymazem — {top_drug}",
                    subtitle="Rozkład wyników posiewu dla najczęściej stosowanego leku",
                    chart_type="bar",
                    labels=tuple(label for label, _ in culture_counts),
                    values=tuple(value for _, value in culture_counts),
                    x_axis_label="Wynik posiewu",
                    y_axis_label="Liczba przypadków",
                )
            )

    no_prior_counts = _culture_counts_for_drug(result, NO_PRIOR_TREATMENT_LABEL)
    if no_prior_counts:
        charts.append(
            AnalysisChartSpec(
                chart_id="pre_swab_no_prior_culture",
                title="Wynik posiewu bez leczenia przed wymazem",
                subtitle="Przypadki z wartością x w polu drug_used_before_micro",
                chart_type="bar",
                labels=tuple(label for label, _ in no_prior_counts),
                values=tuple(value for _, value in no_prior_counts),
                x_axis_label="Wynik posiewu",
                y_axis_label="Liczba przypadków",
            )
        )

    if result.treatment_status_culture_crosstab:
        outcome_labels, series_values = _treatment_status_stacked_series(result)
        if outcome_labels:
            charts.append(
                AnalysisChartSpec(
                    chart_id="pre_swab_treatment_status_culture",
                    title="Status leczenia przed wymazem a wynik posiewu",
                    subtitle=(
                        "Skumulowany rozkład wyników posiewu w dopasowanych "
                        "przypadkach według statusu leczenia"
                    ),
                    chart_type="stacked_bar",
                    labels=TREATMENT_STATUS_ORDER,
                    values=(),
                    stacked_series_labels=outcome_labels,
                    stacked_series_values=series_values,
                    x_axis_label="Status leczenia przed wymazem",
                    y_axis_label="Liczba przypadków",
                )
            )

    return tuple(charts)


def build_breed_treatment_duration_charts(
    result: BreedTreatmentDurationResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success:
        return ()

    charts: list[AnalysisChartSpec] = []

    species_groups: list[tuple[float, ...]] = []
    species_labels: list[str] = []
    if result.dog_duration_days:
        species_groups.append(result.dog_duration_days)
        species_labels.append("Psy")
    if result.cat_duration_days:
        species_groups.append(result.cat_duration_days)
        species_labels.append("Koty")
    if species_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="breed_treatment_species_box",
                title="Czas leczenia uleczonych wrzodów — psy i koty",
                subtitle="Wykres pudełkowy rozkładu czasu leczenia według gatunku",
                chart_type="box",
                labels=tuple(species_labels),
                values=(),
                box_plot_groups=tuple(species_groups),
                x_axis_label="Gatunek",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    if result.dog_breed_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="breed_treatment_dog_breeds_box",
                title="Czas leczenia według rasy — psy",
                subtitle="Najczęstsze rasy (wykres pudełkowy)",
                chart_type="box",
                labels=tuple(group.breed_label for group in result.dog_breed_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.dog_breed_value_groups
                ),
                x_axis_label="Rasa",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    if result.cat_breed_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="breed_treatment_cat_breeds_box",
                title="Czas leczenia według rasy — koty",
                subtitle="Najczęstsze rasy (wykres pudełkowy)",
                chart_type="box",
                labels=tuple(group.breed_label for group in result.cat_breed_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.cat_breed_value_groups
                ),
                x_axis_label="Rasa",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    return tuple(charts)


def build_ulcer_breed_treatment_duration_charts(
    result: UlcerBreedTreatmentDurationResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success:
        return ()

    charts: list[AnalysisChartSpec] = []

    if result.dog_ulcer_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ulcer_breed_dog_ulcer_types_box",
                title="Czas leczenia według typu wrzodu — psy",
                subtitle="Wykres pudełkowy rozkładu czasu leczenia według typu wrzodu",
                chart_type="box",
                labels=tuple(group.ulcer_label for group in result.dog_ulcer_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.dog_ulcer_value_groups
                ),
                x_axis_label="Typ wrzodu",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    if result.cat_ulcer_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ulcer_breed_cat_ulcer_types_box",
                title="Czas leczenia według typu wrzodu — koty",
                subtitle="Wykres pudełkowy rozkładu czasu leczenia według typu wrzodu",
                chart_type="box",
                labels=tuple(group.ulcer_label for group in result.cat_ulcer_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.cat_ulcer_value_groups
                ),
                x_axis_label="Typ wrzodu",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    if result.dog_breed_ulcer_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ulcer_breed_dog_top_breed_ulcer_box",
                title="Czas leczenia — najliczniejsze pary rasa×typ wrzodu (psy)",
                subtitle="Grupy n≥3; wykres pudełkowy",
                chart_type="box",
                labels=tuple(
                    f"{group.breed_label} — {group.ulcer_label}"
                    for group in result.dog_breed_ulcer_value_groups
                ),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.dog_breed_ulcer_value_groups
                ),
                x_axis_label="Rasa — typ wrzodu",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    if result.cat_breed_ulcer_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ulcer_breed_cat_top_breed_ulcer_box",
                title="Czas leczenia — najliczniejsze pary rasa×typ wrzodu (koty)",
                subtitle="Grupy n≥3; wykres pudełkowy",
                chart_type="box",
                labels=tuple(
                    f"{group.breed_label} — {group.ulcer_label}"
                    for group in result.cat_breed_ulcer_value_groups
                ),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.cat_breed_ulcer_value_groups
                ),
                x_axis_label="Rasa — typ wrzodu",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    observed_dog_ulcers = [
        row
        for row in result.dog_ulcer_types
        if row.count > 0 and row.median_days is not None and row.mean_days is not None
    ]
    if observed_dog_ulcers:
        charts.append(
            AnalysisChartSpec(
                chart_id="ulcer_breed_dog_ulcer_median_bar",
                title="Mediana czasu leczenia według typu wrzodu — psy",
                subtitle="Wartość medianowa (mediana) w dniach",
                chart_type="bar",
                labels=tuple(row.ulcer_label for row in observed_dog_ulcers),
                values=tuple(float(row.median_days) for row in observed_dog_ulcers),
                x_axis_label="Typ wrzodu",
                y_axis_label="Mediana (dni)",
            )
        )

    observed_cat_ulcers = [
        row
        for row in result.cat_ulcer_types
        if row.count > 0 and row.median_days is not None and row.mean_days is not None
    ]
    if observed_cat_ulcers:
        charts.append(
            AnalysisChartSpec(
                chart_id="ulcer_breed_cat_ulcer_median_bar",
                title="Mediana czasu leczenia według typu wrzodu — koty",
                subtitle="Wartość medianowa (mediana) w dniach",
                chart_type="bar",
                labels=tuple(row.ulcer_label for row in observed_cat_ulcers),
                values=tuple(float(row.median_days) for row in observed_cat_ulcers),
                x_axis_label="Typ wrzodu",
                y_axis_label="Mediana (dni)",
            )
        )

    return tuple(charts)


def build_ems_treatment_duration_charts(
    result: EmsTreatmentDurationResult,
) -> tuple[AnalysisChartSpec, ...]:
    if not result.is_success:
        return ()

    charts: list[AnalysisChartSpec] = []

    if result.overall_ems_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_overall_box",
                title="Czas leczenia — EMS tak vs EMS nie (łącznie)",
                subtitle="Wykres pudełkowy dla psów i kotów łącznie",
                chart_type="box",
                labels=tuple(group.group_label for group in result.overall_ems_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.overall_ems_value_groups
                ),
                x_axis_label="EMS",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    observed_pooled = [
        row
        for row in result.pooled_ulcer_grouped_bars
        if row.ems_yes_median is not None and row.ems_no_median is not None
    ]
    if observed_pooled:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_pooled_ulcer_grouped_bar",
                title="Mediana czasu leczenia według typu wrzodu — EMS tak vs EMS nie",
                subtitle="Łącznie (psy i koty); mediana w dniach",
                chart_type="grouped_bar",
                labels=tuple(row.ulcer_label for row in observed_pooled),
                values=tuple(float(row.ems_yes_median) for row in observed_pooled),
                secondary_values=tuple(float(row.ems_no_median) for row in observed_pooled),
                x_axis_label="Typ wrzodu",
                y_axis_label="Mediana (dni)",
                legend_note="EMS tak / EMS nie",
            )
        )

    if result.dog_ems_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_dog_overall_box",
                title="Czas leczenia — EMS tak vs EMS nie (psy)",
                subtitle="Wykres pudełkowy",
                chart_type="box",
                labels=tuple(group.group_label for group in result.dog_ems_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.dog_ems_value_groups
                ),
                x_axis_label="EMS",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    if result.cat_ems_value_groups:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_cat_overall_box",
                title="Czas leczenia — EMS tak vs EMS nie (koty)",
                subtitle="Wykres pudełkowy",
                chart_type="box",
                labels=tuple(group.group_label for group in result.cat_ems_value_groups),
                values=(),
                box_plot_groups=tuple(
                    group.duration_days for group in result.cat_ems_value_groups
                ),
                x_axis_label="EMS",
                y_axis_label="Czas leczenia (dni)",
            )
        )

    observed_dog_ulcers = [
        row
        for row in result.dog_ulcer_grouped_bars
        if row.ems_yes_median is not None and row.ems_no_median is not None
    ]
    if observed_dog_ulcers:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_dog_ulcer_grouped_bar",
                title="Mediana czasu leczenia według typu wrzodu — psy",
                subtitle="EMS tak vs EMS nie; mediana w dniach",
                chart_type="grouped_bar",
                labels=tuple(row.ulcer_label for row in observed_dog_ulcers),
                values=tuple(float(row.ems_yes_median) for row in observed_dog_ulcers),
                secondary_values=tuple(float(row.ems_no_median) for row in observed_dog_ulcers),
                x_axis_label="Typ wrzodu",
                y_axis_label="Mediana (dni)",
                legend_note="EMS tak / EMS nie",
            )
        )

    observed_cat_ulcers = [
        row
        for row in result.cat_ulcer_grouped_bars
        if row.ems_yes_median is not None and row.ems_no_median is not None
    ]
    if observed_cat_ulcers:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_cat_ulcer_grouped_bar",
                title="Mediana czasu leczenia według typu wrzodu — koty",
                subtitle="EMS tak vs EMS nie; mediana w dniach",
                chart_type="grouped_bar",
                labels=tuple(row.ulcer_label for row in observed_cat_ulcers),
                values=tuple(float(row.ems_yes_median) for row in observed_cat_ulcers),
                secondary_values=tuple(float(row.ems_no_median) for row in observed_cat_ulcers),
                x_axis_label="Typ wrzodu",
                y_axis_label="Mediana (dni)",
                legend_note="EMS tak / EMS nie",
            )
        )

    breed_rows = [
        comparison
        for comparison in result.dog_breed_comparisons
        if comparison.ems_yes is not None
        and comparison.ems_no is not None
        and comparison.ems_yes.median_days is not None
        and comparison.ems_no.median_days is not None
    ][:8]
    if breed_rows:
        charts.append(
            AnalysisChartSpec(
                chart_id="ems_treatment_dog_breed_grouped_bar",
                title="Mediana czasu leczenia według rasy — psy",
                subtitle="EMS tak vs EMS nie; najliczniejsze rasy",
                chart_type="grouped_bar",
                labels=tuple(row.breed_label for row in breed_rows),
                values=tuple(float(row.ems_yes.median_days) for row in breed_rows),
                secondary_values=tuple(float(row.ems_no.median_days) for row in breed_rows),
                x_axis_label="Rasa",
                y_axis_label="Mediana (dni)",
                legend_note="EMS tak / EMS nie",
            )
        )

    return tuple(charts)
