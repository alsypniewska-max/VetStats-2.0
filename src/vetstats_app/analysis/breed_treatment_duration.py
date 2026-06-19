from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from vetstats_app.analysis.clinical_common import (
    ExtendedDurationSummaryStats,
    build_patient_species_breed_lookup,
    classify_species,
    format_optional_number,
    normalize_breed,
    resolve_column,
    summarize_duration_values_extended,
)
from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.analysis.treatment_cases import (
    TreatmentCaseExclusionSummary,
    filter_healed_cases_with_duration,
)

MIN_GROUP_SIZE = 5
MIN_BREEDS_FOR_KRUSKAL = 3
TOP_BREED_CHART_LIMIT = 8

SPECIES_LABELS = {
    "dog": "Psy",
    "cat": "Koty",
}


@dataclass(frozen=True)
class BreedTreatmentDurationExclusions:
    total_clinical_rows: int
    excluded_non_ulcer: int
    excluded_not_good: int
    excluded_enucleation: int
    excluded_no_followup: int
    excluded_continuation: int
    excluded_duration_unavailable: int
    included_healed_with_duration: int
    excluded_unknown_species: int
    excluded_unknown_breed: int
    included_with_known_species: int
    included_with_known_breed: int


@dataclass(frozen=True)
class TreatmentDurationGroupRow:
    group_label: str
    count: int
    mean_days: float | None
    median_days: float | None
    min_days: float | None
    max_days: float | None
    percentile_25_days: float | None
    percentile_75_days: float | None


@dataclass(frozen=True)
class BreedDurationValueGroup:
    species: str
    breed_label: str
    duration_days: tuple[float, ...]


@dataclass(frozen=True)
class StatisticalTestRow:
    comparison_label: str
    test_name: str
    statistic: str
    p_value: str
    note: str


@dataclass(frozen=True)
class BreedTreatmentDurationResult:
    source_clinical_label: str
    source_patient_label: str
    exclusions: BreedTreatmentDurationExclusions
    dog_summary: TreatmentDurationGroupRow | None
    cat_summary: TreatmentDurationGroupRow | None
    dog_breeds: tuple[TreatmentDurationGroupRow, ...]
    cat_breeds: tuple[TreatmentDurationGroupRow, ...]
    statistical_tests: tuple[StatisticalTestRow, ...]
    dog_duration_days: tuple[float, ...]
    cat_duration_days: tuple[float, ...]
    dog_breed_value_groups: tuple[BreedDurationValueGroup, ...]
    cat_breed_value_groups: tuple[BreedDurationValueGroup, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


@dataclass(frozen=True)
class _EnrichedHealedCase:
    duration_days: int
    species: str
    breed: str | None


def _stats_row(label: str, values: tuple[float, ...]) -> TreatmentDurationGroupRow | None:
    stats = summarize_duration_values_extended(values)
    if stats.count == 0:
        return None
    return TreatmentDurationGroupRow(
        group_label=label,
        count=stats.count,
        mean_days=stats.mean_days,
        median_days=stats.median_days,
        min_days=stats.min_days,
        max_days=stats.max_days,
        percentile_25_days=stats.percentile_25_days,
        percentile_75_days=stats.percentile_75_days,
    )


def _group_stats_rows(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
) -> tuple[TreatmentDurationGroupRow, ...]:
    by_breed: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        if case.species != species or case.breed is None:
            continue
        by_breed[case.breed].append(float(case.duration_days))

    rows: list[TreatmentDurationGroupRow] = []
    for breed, values in sorted(
        by_breed.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        row = _stats_row(breed, tuple(values))
        if row is not None:
            rows.append(row)
    return tuple(rows)


def _breed_value_groups(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
    limit: int = TOP_BREED_CHART_LIMIT,
) -> tuple[BreedDurationValueGroup, ...]:
    breed_rows = _group_stats_rows(cases, species=species)
    groups: list[BreedDurationValueGroup] = []
    for row in breed_rows[:limit]:
        values = tuple(
            float(case.duration_days)
            for case in cases
            if case.species == species and case.breed == row.group_label
        )
        if values:
            groups.append(
                BreedDurationValueGroup(
                    species=species,
                    breed_label=row.group_label,
                    duration_days=values,
                )
            )
    return tuple(groups)


def _mann_whitney_test(
    dog_values: tuple[float, ...],
    cat_values: tuple[float, ...],
) -> StatisticalTestRow:
    label = "Psy vs koty — czas leczenia"
    if len(dog_values) < MIN_GROUP_SIZE or len(cat_values) < MIN_GROUP_SIZE:
        return StatisticalTestRow(
            comparison_label=label,
            test_name="Mann–Whitney U",
            statistic="—",
            p_value="—",
            note="test niedostępny (za mała liczba przypadków)",
        )
    try:
        from scipy.stats import mannwhitneyu

        statistic, p_value = mannwhitneyu(
            dog_values,
            cat_values,
            alternative="two-sided",
        )
        return StatisticalTestRow(
            comparison_label=label,
            test_name="Mann–Whitney U",
            statistic=f"{statistic:.4f}",
            p_value=f"{p_value:.4f}",
            note="",
        )
    except Exception:
        return StatisticalTestRow(
            comparison_label=label,
            test_name="Mann–Whitney U",
            statistic="—",
            p_value="—",
            note="test niedostępny (błąd obliczeń)",
        )


def _kruskal_wallis_test(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
) -> StatisticalTestRow:
    species_label = SPECIES_LABELS[species]
    label = f"{species_label} — czas leczenia między rasami"
    by_breed: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        if case.species != species or case.breed is None:
            continue
        by_breed[case.breed].append(float(case.duration_days))

    eligible_groups = [
        values for values in by_breed.values() if len(values) >= MIN_GROUP_SIZE
    ]
    if len(eligible_groups) < MIN_BREEDS_FOR_KRUSKAL:
        return StatisticalTestRow(
            comparison_label=label,
            test_name="Kruskal–Wallis",
            statistic="—",
            p_value="—",
            note="test niedostępny (za mała liczba przypadków)",
        )
    try:
        from scipy.stats import kruskal

        statistic, p_value = kruskal(*eligible_groups)
        return StatisticalTestRow(
            comparison_label=label,
            test_name="Kruskal–Wallis",
            statistic=f"{statistic:.4f}",
            p_value=f"{p_value:.4f}",
            note="",
        )
    except Exception:
        return StatisticalTestRow(
            comparison_label=label,
            test_name="Kruskal–Wallis",
            statistic="—",
            p_value="—",
            note="test niedostępny (błąd obliczeń)",
        )


def _build_exclusions(
    case_summary: TreatmentCaseExclusionSummary,
    *,
    excluded_unknown_species: int,
    excluded_unknown_breed: int,
    included_with_known_species: int,
    included_with_known_breed: int,
) -> BreedTreatmentDurationExclusions:
    return BreedTreatmentDurationExclusions(
        total_clinical_rows=case_summary.total_clinical_rows,
        excluded_non_ulcer=case_summary.excluded_non_ulcer,
        excluded_not_good=case_summary.excluded_not_good,
        excluded_enucleation=case_summary.excluded_enucleation,
        excluded_no_followup=case_summary.excluded_no_followup,
        excluded_continuation=case_summary.excluded_continuation,
        excluded_duration_unavailable=case_summary.excluded_duration_unavailable,
        included_healed_with_duration=case_summary.included_healed_with_duration,
        excluded_unknown_species=excluded_unknown_species,
        excluded_unknown_breed=excluded_unknown_breed,
        included_with_known_species=included_with_known_species,
        included_with_known_breed=included_with_known_breed,
    )


def compute_breed_treatment_duration(
    clinical: pd.DataFrame,
    patient: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_patient_label: str = "patient",
) -> BreedTreatmentDurationResult:
    from data_sterilizer.schemas.patient import PATIENT_ID_COLUMN

    patient_id_col = resolve_column(patient, PATIENT_ID_COLUMN)
    if patient_id_col is None:
        empty_case_summary = TreatmentCaseExclusionSummary(
            total_clinical_rows=len(clinical),
            excluded_non_ulcer=0,
            excluded_not_good=0,
            excluded_enucleation=0,
            excluded_no_followup=0,
            excluded_continuation=0,
            excluded_duration_unavailable=0,
            included_healed_with_duration=0,
        )
        exclusions = _build_exclusions(
            empty_case_summary,
            excluded_unknown_species=0,
            excluded_unknown_breed=0,
            included_with_known_species=0,
            included_with_known_breed=0,
        )
        return BreedTreatmentDurationResult(
            source_clinical_label=source_clinical_label,
            source_patient_label=source_patient_label,
            exclusions=exclusions,
            dog_summary=None,
            cat_summary=None,
            dog_breeds=(),
            cat_breeds=(),
            statistical_tests=(),
            dog_duration_days=(),
            cat_duration_days=(),
            dog_breed_value_groups=(),
            cat_breed_value_groups=(),
            error_message="Brak kolumny patient_ID w tabeli patient.",
        )

    healed_cases, case_summary = filter_healed_cases_with_duration(clinical)
    lookup = build_patient_species_breed_lookup(patient)

    excluded_unknown_species = 0
    excluded_unknown_breed = 0
    enriched_cases: list[_EnrichedHealedCase] = []

    for case in healed_cases:
        species_value, breed_value = lookup.get(case.patient_id, (None, None))
        species = classify_species(species_value)
        if species is None:
            excluded_unknown_species += 1
            continue

        breed = normalize_breed(breed_value)
        if breed is None:
            excluded_unknown_breed += 1
            enriched_cases.append(
                _EnrichedHealedCase(
                    duration_days=case.duration_days,
                    species=species,
                    breed=None,
                )
            )
            continue

        enriched_cases.append(
            _EnrichedHealedCase(
                duration_days=case.duration_days,
                species=species,
                breed=breed,
            )
        )

    cases_tuple = tuple(enriched_cases)
    cases_with_breed = tuple(case for case in cases_tuple if case.breed is not None)
    included_with_known_species = len(cases_tuple)
    included_with_known_breed = len(cases_with_breed)

    exclusions = _build_exclusions(
        case_summary,
        excluded_unknown_species=excluded_unknown_species,
        excluded_unknown_breed=excluded_unknown_breed,
        included_with_known_species=included_with_known_species,
        included_with_known_breed=included_with_known_breed,
    )

    dog_duration_days = tuple(
        float(case.duration_days) for case in cases_tuple if case.species == "dog"
    )
    cat_duration_days = tuple(
        float(case.duration_days) for case in cases_tuple if case.species == "cat"
    )

    dog_summary = _stats_row(SPECIES_LABELS["dog"], dog_duration_days)
    cat_summary = _stats_row(SPECIES_LABELS["cat"], cat_duration_days)
    dog_breeds = _group_stats_rows(cases_with_breed, species="dog")
    cat_breeds = _group_stats_rows(cases_with_breed, species="cat")

    statistical_tests = (
        _mann_whitney_test(dog_duration_days, cat_duration_days),
        _kruskal_wallis_test(cases_with_breed, species="dog"),
        _kruskal_wallis_test(cases_with_breed, species="cat"),
    )

    return BreedTreatmentDurationResult(
        source_clinical_label=source_clinical_label,
        source_patient_label=source_patient_label,
        exclusions=exclusions,
        dog_summary=dog_summary,
        cat_summary=cat_summary,
        dog_breeds=dog_breeds,
        cat_breeds=cat_breeds,
        statistical_tests=statistical_tests,
        dog_duration_days=dog_duration_days,
        cat_duration_days=cat_duration_days,
        dog_breed_value_groups=_breed_value_groups(cases_with_breed, species="dog"),
        cat_breed_value_groups=_breed_value_groups(cases_with_breed, species="cat"),
    )


def _duration_group_row_cells(row: TreatmentDurationGroupRow) -> tuple[str, ...]:
    return (
        row.group_label,
        str(row.count),
        format_optional_number(row.mean_days),
        format_optional_number(row.median_days),
        format_optional_number(row.min_days),
        format_optional_number(row.max_days),
        format_optional_number(row.percentile_25_days),
        format_optional_number(row.percentile_75_days),
    )


_DURATION_TABLE_COLUMNS = (
    "Grupa",
    "Liczba",
    "Średnia (dni)",
    "Mediana (dni)",
    "Min (dni)",
    "Max (dni)",
    "P25 (dni)",
    "P75 (dni)",
)


def build_summary_details(result: BreedTreatmentDurationResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przeanalizować czasu leczenia."

    exclusions = result.exclusions
    return (
        f"Źródła danych: {result.source_clinical_label}, {result.source_patient_label}. "
        f"Uwzględniono {exclusions.included_with_known_breed} uleczonych przypadków "
        f"z znaną rasą (z {exclusions.included_healed_with_duration} uleczonych z "
        f"obliczonym czasem leczenia). "
        f"Wykluczono m.in. {exclusions.excluded_unknown_species} przypadków z nieznaną "
        f"gatunkiem oraz {exclusions.excluded_unknown_breed} z nieznaną rasą."
    )


def build_interpretation_summary(result: BreedTreatmentDurationResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przygotować interpretacji."

    exclusions = result.exclusions
    if exclusions.included_healed_with_duration == 0:
        return (
            "Brak uleczonych przypadków wrzodowych z obliczalnym czasem leczenia "
            "do analizy rasowej."
        )

    parts = [
        (
            f"Po zastosowaniu filtrów uleczonych przypadków (how_ended = good) "
            f"z obliczonym czasem leczenia pozostało "
            f"{exclusions.included_healed_with_duration} przypadków; "
            f"{exclusions.included_with_known_species} ma znany gatunek, "
            f"a {exclusions.included_with_known_breed} — znaną rasę."
        )
    ]

    if result.dog_summary and result.cat_summary:
        parts.append(
            f"Łącznie dla psów mediana czasu leczenia wynosi "
            f"{format_optional_number(result.dog_summary.median_days)} dni "
            f"(n={result.dog_summary.count}), a dla kotów "
            f"{format_optional_number(result.cat_summary.median_days)} dni "
            f"(n={result.cat_summary.count})."
        )
    elif result.dog_summary:
        parts.append(
            f"Dostępne są wyłącznie dane dla psów: mediana "
            f"{format_optional_number(result.dog_summary.median_days)} dni "
            f"(n={result.dog_summary.count})."
        )
    elif result.cat_summary:
        parts.append(
            f"Dostępne są wyłącznie dane dla kotów: mediana "
            f"{format_optional_number(result.cat_summary.median_days)} dni "
            f"(n={result.cat_summary.count})."
        )

    for test in result.statistical_tests:
        if test.note:
            parts.append(f"{test.comparison_label}: {test.note}.")
        else:
            parts.append(
                f"{test.comparison_label} ({test.test_name}): p={test.p_value}."
            )

    if exclusions.excluded_unknown_breed > 0:
        parts.append(
            "Podsumowanie według gatunku obejmuje przypadki ze znaną rasą i bez "
            f"znanej rasy; w tabelach rasowych uwzględniono wyłącznie "
            f"{exclusions.included_with_known_breed} przypadków ze znaną rasą "
            f"({exclusions.excluded_unknown_breed} wykluczono z powodu nieznanej rasy)."
        )

    if result.dog_summary and result.dog_breeds:
        top_dog = result.dog_breeds[0]
        parts.append(
            f"Wśród psów najwięcej uleczonych przypadków dotyczy rasy {top_dog.group_label} "
            f"(n={top_dog.count}, mediana {format_optional_number(top_dog.median_days)} dni)."
        )
    if result.cat_breeds:
        top_cat = result.cat_breeds[0]
        parts.append(
            f"Wśród kotów najwięcej uleczonych przypadków dotyczy rasy {top_cat.group_label} "
            f"(n={top_cat.count}, mediana {format_optional_number(top_cat.median_days)} dni)."
        )

    return " ".join(parts)


def build_descriptive_stats_block(
    result: BreedTreatmentDurationResult,
) -> ReportTableBlock:
    exclusions = result.exclusions
    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba wierszy clinical (N)", str(exclusions.total_clinical_rows)),
            ("Wykluczone — nie wrzód (n)", str(exclusions.excluded_non_ulcer)),
            ("Wykluczone — inne zakończenie niż good (n)", str(exclusions.excluded_not_good)),
            ("Wykluczone — enukleacja (n)", str(exclusions.excluded_enucleation)),
            ("Wykluczone — brak kontroli (n)", str(exclusions.excluded_no_followup)),
            ("Wykluczone — kontynuacja leczenia (n)", str(exclusions.excluded_continuation)),
            (
                "Wykluczone — brak obliczalnego czasu leczenia (n)",
                str(exclusions.excluded_duration_unavailable),
            ),
            (
                "Uwzględnione — uleczone z czasem leczenia (n)",
                str(exclusions.included_healed_with_duration),
            ),
            ("Wykluczone — nieznany gatunek (n)", str(exclusions.excluded_unknown_species)),
            ("Wykluczone — nieznana rasa (n)", str(exclusions.excluded_unknown_breed)),
            ("Uwzględnione — znany gatunek (n)", str(exclusions.included_with_known_species)),
            ("Uwzględnione — znana rasa (n)", str(exclusions.included_with_known_breed)),
            ("Liczba ras — psy (n)", str(len(result.dog_breeds))),
            ("Liczba ras — koty (n)", str(len(result.cat_breeds))),
        ),
    )


def exclusions_table_block(result: BreedTreatmentDurationResult) -> ReportTableBlock:
    exclusions = result.exclusions
    return ReportTableBlock(
        title="Podsumowanie wykluczeń",
        columns=("Kategoria wykluczenia", "Liczba"),
        rows=(
            ("Nie wrzód", str(exclusions.excluded_non_ulcer)),
            ("Inne zakończenie niż good", str(exclusions.excluded_not_good)),
            ("Enukleacja", str(exclusions.excluded_enucleation)),
            ("Brak kontroli", str(exclusions.excluded_no_followup)),
            ("Kontynuacja leczenia", str(exclusions.excluded_continuation)),
            ("Brak obliczalnego czasu leczenia", str(exclusions.excluded_duration_unavailable)),
            ("Nieznany gatunek", str(exclusions.excluded_unknown_species)),
            ("Nieznana rasa", str(exclusions.excluded_unknown_breed)),
        ),
    )


def species_summary_table_block(result: BreedTreatmentDurationResult) -> ReportTableBlock:
    rows: list[tuple[str, ...]] = []
    if result.dog_summary is not None:
        rows.append(_duration_group_row_cells(result.dog_summary))
    if result.cat_summary is not None:
        rows.append(_duration_group_row_cells(result.cat_summary))
    return ReportTableBlock(
        title=(
            "Czas leczenia według gatunku "
            "(znany gatunek — także bez znanej rasy)"
        ),
        columns=_DURATION_TABLE_COLUMNS,
        rows=tuple(rows),
    )


def dog_breeds_table_block(result: BreedTreatmentDurationResult) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia według rasy — psy (tylko znana rasa)",
        columns=("Rasa", *_DURATION_TABLE_COLUMNS[1:]),
        rows=tuple(
            (row.group_label, *_duration_group_row_cells(row)[1:])
            for row in result.dog_breeds
        ),
    )


def cat_breeds_table_block(result: BreedTreatmentDurationResult) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia według rasy — koty (tylko znana rasa)",
        columns=("Rasa", *_DURATION_TABLE_COLUMNS[1:]),
        rows=tuple(
            (row.group_label, *_duration_group_row_cells(row)[1:])
            for row in result.cat_breeds
        ),
    )


def statistical_tests_table_block(
    result: BreedTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Porównania statystyczne",
        columns=("Porównanie", "Test", "Statystyka", "p-value", "Uwagi"),
        rows=tuple(
            (
                row.comparison_label,
                row.test_name,
                row.statistic,
                row.p_value,
                row.note or "—",
            )
            for row in result.statistical_tests
        ),
    )
