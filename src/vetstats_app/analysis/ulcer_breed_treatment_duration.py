from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from vetstats_app.analysis.clinical_common import (
    build_patient_species_breed_lookup,
    classify_species,
    format_optional_number,
    normalize_breed,
    normalize_ulcer_code,
    resolve_column,
    summarize_duration_values_extended,
)
from vetstats_app.analysis.diagnosis_frequency import DIAGNOSIS_LABELS
from vetstats_app.analysis.report_models import ReportTableBlock
from vetstats_app.analysis.treatment_cases import (
    TreatmentCaseExclusionSummary,
    filter_healed_cases_with_duration,
)

MIN_DISPLAY_GROUP_SIZE = 3
TOP_BREED_ULCER_CHART_LIMIT = 8

SPECIES_LABELS = {
    "dog": "Psy",
    "cat": "Koty",
}


@dataclass(frozen=True)
class UlcerBreedTreatmentDurationExclusions:
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
    excluded_invalid_ulcer: int
    excluded_below_min_n: int
    included_with_known_species: int
    included_with_known_breed: int
    included_in_breed_ulcer_tables: int


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
class UlcerTypeDurationRow(TreatmentDurationGroupRow):
    ulcer_code: str
    ulcer_label: str


@dataclass(frozen=True)
class BreedUlcerDurationRow(TreatmentDurationGroupRow):
    breed_label: str
    ulcer_code: str
    ulcer_label: str


@dataclass(frozen=True)
class UlcerDurationValueGroup:
    species: str
    ulcer_code: str
    ulcer_label: str
    duration_days: tuple[float, ...]


@dataclass(frozen=True)
class BreedUlcerDurationValueGroup:
    species: str
    breed_label: str
    ulcer_code: str
    ulcer_label: str
    duration_days: tuple[float, ...]


@dataclass(frozen=True)
class UlcerBreedTreatmentDurationResult:
    source_clinical_label: str
    source_patient_label: str
    exclusions: UlcerBreedTreatmentDurationExclusions
    dog_ulcer_types: tuple[UlcerTypeDurationRow, ...]
    cat_ulcer_types: tuple[UlcerTypeDurationRow, ...]
    dog_breed_ulcer_rows: tuple[BreedUlcerDurationRow, ...]
    cat_breed_ulcer_rows: tuple[BreedUlcerDurationRow, ...]
    dog_ulcer_value_groups: tuple[UlcerDurationValueGroup, ...]
    cat_ulcer_value_groups: tuple[UlcerDurationValueGroup, ...]
    dog_breed_ulcer_value_groups: tuple[BreedUlcerDurationValueGroup, ...]
    cat_breed_ulcer_value_groups: tuple[BreedUlcerDurationValueGroup, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


@dataclass(frozen=True)
class _EnrichedHealedCase:
    duration_days: int
    species: str
    breed: str | None
    ulcer_code: str
    ulcer_label: str


def _ulcer_label(ulcer_code: str) -> str:
    return DIAGNOSIS_LABELS.get(ulcer_code, ulcer_code)


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

_BREED_ULCER_TABLE_COLUMNS = (
    "Rasa",
    "Typ wrzodu",
    "Liczba",
    "Średnia (dni)",
    "Mediana (dni)",
    "Min (dni)",
    "Max (dni)",
    "P25 (dni)",
    "P75 (dni)",
)


def _ulcer_type_rows(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
) -> tuple[UlcerTypeDurationRow, ...]:
    by_ulcer: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        if case.species != species:
            continue
        by_ulcer[case.ulcer_code].append(float(case.duration_days))

    rows: list[UlcerTypeDurationRow] = []
    for ulcer_code, values in sorted(
        by_ulcer.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        ulcer_label = _ulcer_label(ulcer_code)
        base_row = _stats_row(ulcer_label, tuple(values))
        if base_row is None:
            continue
        rows.append(
            UlcerTypeDurationRow(
                group_label=base_row.group_label,
                count=base_row.count,
                mean_days=base_row.mean_days,
                median_days=base_row.median_days,
                min_days=base_row.min_days,
                max_days=base_row.max_days,
                percentile_25_days=base_row.percentile_25_days,
                percentile_75_days=base_row.percentile_75_days,
                ulcer_code=ulcer_code,
                ulcer_label=ulcer_label,
            )
        )
    return tuple(rows)


def _breed_ulcer_cell_counts(
    cases: tuple[_EnrichedHealedCase, ...],
) -> dict[tuple[str, str, str], int]:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for case in cases:
        if case.breed is None:
            continue
        counts[(case.species, case.breed, case.ulcer_code)] += 1
    return counts


def _cases_for_displayed_breed_ulcer_groups(
    cases: tuple[_EnrichedHealedCase, ...],
    cell_counts: dict[tuple[str, str, str], int],
) -> tuple[tuple[_EnrichedHealedCase, ...], int]:
    excluded_below_min_n = 0
    displayed: list[_EnrichedHealedCase] = []
    for case in cases:
        if case.breed is None:
            continue
        key = (case.species, case.breed, case.ulcer_code)
        if cell_counts[key] < MIN_DISPLAY_GROUP_SIZE:
            excluded_below_min_n += 1
            continue
        displayed.append(case)
    return tuple(displayed), excluded_below_min_n


def _breed_ulcer_rows(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
) -> tuple[BreedUlcerDurationRow, ...]:
    by_cell: dict[tuple[str, str], list[float]] = defaultdict(list)
    for case in cases:
        if case.species != species or case.breed is None:
            continue
        by_cell[(case.breed, case.ulcer_code)].append(float(case.duration_days))

    rows: list[BreedUlcerDurationRow] = []
    for (breed, ulcer_code), values in sorted(
        by_cell.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    ):
        ulcer_label = _ulcer_label(ulcer_code)
        base_row = _stats_row(f"{breed} — {ulcer_label}", tuple(values))
        if base_row is None:
            continue
        rows.append(
            BreedUlcerDurationRow(
                group_label=base_row.group_label,
                count=base_row.count,
                mean_days=base_row.mean_days,
                median_days=base_row.median_days,
                min_days=base_row.min_days,
                max_days=base_row.max_days,
                percentile_25_days=base_row.percentile_25_days,
                percentile_75_days=base_row.percentile_75_days,
                breed_label=breed,
                ulcer_code=ulcer_code,
                ulcer_label=ulcer_label,
            )
        )
    return tuple(rows)


def _ulcer_value_groups(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
) -> tuple[UlcerDurationValueGroup, ...]:
    ulcer_rows = _ulcer_type_rows(cases, species=species)
    groups: list[UlcerDurationValueGroup] = []
    for row in ulcer_rows:
        values = tuple(
            float(case.duration_days)
            for case in cases
            if case.species == species and case.ulcer_code == row.ulcer_code
        )
        if values:
            groups.append(
                UlcerDurationValueGroup(
                    species=species,
                    ulcer_code=row.ulcer_code,
                    ulcer_label=row.ulcer_label,
                    duration_days=values,
                )
            )
    return tuple(groups)


def _breed_ulcer_value_groups(
    cases: tuple[_EnrichedHealedCase, ...],
    *,
    species: str,
    limit: int = TOP_BREED_ULCER_CHART_LIMIT,
) -> tuple[BreedUlcerDurationValueGroup, ...]:
    breed_ulcer_rows = _breed_ulcer_rows(cases, species=species)
    groups: list[BreedUlcerDurationValueGroup] = []
    for row in breed_ulcer_rows[:limit]:
        values = tuple(
            float(case.duration_days)
            for case in cases
            if (
                case.species == species
                and case.breed == row.breed_label
                and case.ulcer_code == row.ulcer_code
            )
        )
        if values:
            groups.append(
                BreedUlcerDurationValueGroup(
                    species=species,
                    breed_label=row.breed_label,
                    ulcer_code=row.ulcer_code,
                    ulcer_label=row.ulcer_label,
                    duration_days=values,
                )
            )
    return tuple(groups)


def _build_exclusions(
    case_summary: TreatmentCaseExclusionSummary,
    *,
    excluded_unknown_species: int,
    excluded_unknown_breed: int,
    excluded_invalid_ulcer: int,
    excluded_below_min_n: int,
    included_with_known_species: int,
    included_with_known_breed: int,
    included_in_breed_ulcer_tables: int,
) -> UlcerBreedTreatmentDurationExclusions:
    return UlcerBreedTreatmentDurationExclusions(
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
        excluded_invalid_ulcer=excluded_invalid_ulcer,
        excluded_below_min_n=excluded_below_min_n,
        included_with_known_species=included_with_known_species,
        included_with_known_breed=included_with_known_breed,
        included_in_breed_ulcer_tables=included_in_breed_ulcer_tables,
    )


def _empty_exclusions(case_summary: TreatmentCaseExclusionSummary) -> UlcerBreedTreatmentDurationExclusions:
    return _build_exclusions(
        case_summary,
        excluded_unknown_species=0,
        excluded_unknown_breed=0,
        excluded_invalid_ulcer=0,
        excluded_below_min_n=0,
        included_with_known_species=0,
        included_with_known_breed=0,
        included_in_breed_ulcer_tables=0,
    )


def compute_ulcer_breed_treatment_duration(
    clinical: pd.DataFrame,
    patient: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_patient_label: str = "patient",
) -> UlcerBreedTreatmentDurationResult:
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
        return UlcerBreedTreatmentDurationResult(
            source_clinical_label=source_clinical_label,
            source_patient_label=source_patient_label,
            exclusions=_empty_exclusions(empty_case_summary),
            dog_ulcer_types=(),
            cat_ulcer_types=(),
            dog_breed_ulcer_rows=(),
            cat_breed_ulcer_rows=(),
            dog_ulcer_value_groups=(),
            cat_ulcer_value_groups=(),
            dog_breed_ulcer_value_groups=(),
            cat_breed_ulcer_value_groups=(),
            error_message="Brak kolumny patient_ID w tabeli patient.",
        )

    healed_cases, case_summary = filter_healed_cases_with_duration(clinical)
    lookup = build_patient_species_breed_lookup(patient)

    excluded_unknown_species = 0
    excluded_unknown_breed = 0
    excluded_invalid_ulcer = 0
    species_ulcer_cases: list[_EnrichedHealedCase] = []
    breed_ulcer_cases: list[_EnrichedHealedCase] = []

    for case in healed_cases:
        species_value, breed_value = lookup.get(case.patient_id, (None, None))
        species = classify_species(species_value)
        if species is None:
            excluded_unknown_species += 1
            continue

        ulcer_code = normalize_ulcer_code(case.terminal_ulcer_code)
        if ulcer_code is None:
            excluded_invalid_ulcer += 1
            continue

        ulcer_label = _ulcer_label(ulcer_code)
        breed = normalize_breed(breed_value)
        enriched = _EnrichedHealedCase(
            duration_days=case.duration_days,
            species=species,
            breed=breed,
            ulcer_code=ulcer_code,
            ulcer_label=ulcer_label,
        )
        species_ulcer_cases.append(enriched)
        if breed is None:
            excluded_unknown_breed += 1
            continue
        breed_ulcer_cases.append(enriched)

    species_ulcer_tuple = tuple(species_ulcer_cases)
    breed_ulcer_tuple = tuple(breed_ulcer_cases)
    cell_counts = _breed_ulcer_cell_counts(breed_ulcer_tuple)
    displayed_breed_ulcer_cases, excluded_below_min_n = (
        _cases_for_displayed_breed_ulcer_groups(breed_ulcer_tuple, cell_counts)
    )

    exclusions = _build_exclusions(
        case_summary,
        excluded_unknown_species=excluded_unknown_species,
        excluded_unknown_breed=excluded_unknown_breed,
        excluded_invalid_ulcer=excluded_invalid_ulcer,
        excluded_below_min_n=excluded_below_min_n,
        included_with_known_species=len(species_ulcer_tuple),
        included_with_known_breed=len(breed_ulcer_tuple),
        included_in_breed_ulcer_tables=len(displayed_breed_ulcer_cases),
    )

    return UlcerBreedTreatmentDurationResult(
        source_clinical_label=source_clinical_label,
        source_patient_label=source_patient_label,
        exclusions=exclusions,
        dog_ulcer_types=_ulcer_type_rows(species_ulcer_tuple, species="dog"),
        cat_ulcer_types=_ulcer_type_rows(species_ulcer_tuple, species="cat"),
        dog_breed_ulcer_rows=_breed_ulcer_rows(displayed_breed_ulcer_cases, species="dog"),
        cat_breed_ulcer_rows=_breed_ulcer_rows(displayed_breed_ulcer_cases, species="cat"),
        dog_ulcer_value_groups=_ulcer_value_groups(species_ulcer_tuple, species="dog"),
        cat_ulcer_value_groups=_ulcer_value_groups(species_ulcer_tuple, species="cat"),
        dog_breed_ulcer_value_groups=_breed_ulcer_value_groups(
            displayed_breed_ulcer_cases,
            species="dog",
        ),
        cat_breed_ulcer_value_groups=_breed_ulcer_value_groups(
            displayed_breed_ulcer_cases,
            species="cat",
        ),
    )


def build_summary_details(result: UlcerBreedTreatmentDurationResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przeanalizować czasu leczenia."

    exclusions = result.exclusions
    return (
        f"Źródła danych: {result.source_clinical_label}, {result.source_patient_label}. "
        f"Analiza opiera się na uleczonych przypadkach z obliczonym czasem leczenia "
        f"i kategoryzacji według terminal_ulcer_code. "
        f"Uwzględniono {exclusions.included_with_known_species} przypadków ze znanym "
        f"gatunkiem i prawidłowym typem wrzodu; "
        f"{exclusions.included_in_breed_ulcer_tables} trafiło do tabel rasa×typ wrzodu "
        f"(grupy n≥{MIN_DISPLAY_GROUP_SIZE}). "
        f"Wykluczono m.in. {exclusions.excluded_below_min_n} przypadków w grupach "
        f"rasa×typ wrzodu z n<{MIN_DISPLAY_GROUP_SIZE}."
    )


def build_interpretation_summary(result: UlcerBreedTreatmentDurationResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przygotować interpretacji."

    exclusions = result.exclusions
    if exclusions.included_healed_with_duration == 0:
        return (
            "Brak uleczonych przypadków wrzodowych z obliczalnym czasem leczenia "
            "do analizy typu wrzodu w obrębie ras."
        )

    parts = [
        (
            "Psy i koty są analizowane osobno — wyniki gatunkowe i rasowe nie są "
            "łączone między gatunkami."
        ),
        (
            "Typ wrzodu przypisany jest na podstawie terminal_ulcer_code uleczonych "
            "przypadków (kod z wiersza kończącego leczenie), a nie dowolnych wartości "
            "type_of_ulcer z całej historii wizyt."
        ),
        (
            f"Po filtrach uleczonych przypadków pozostało "
            f"{exclusions.included_healed_with_duration} przypadków; "
            f"{exclusions.included_with_known_species} ma znany gatunek i prawidłowy "
            f"typ wrzodu, a {exclusions.included_with_known_breed} — dodatkowo znaną rasę."
        ),
        (
            f"Tabele rasa×typ wrzodu pokazują wyłącznie grupy z co najmniej "
            f"{MIN_DISPLAY_GROUP_SIZE} przypadkami (n≥{MIN_DISPLAY_GROUP_SIZE}). "
            f"{exclusions.excluded_below_min_n} przypadków ze znaną rasą i typem wrzodu "
            f"znajduje się w mniejszych grupach i jest wyłączonych z głównych tabel "
            f"i wykresów, ale uwzględnionych w podsumowaniu wykluczeń."
        ),
    ]

    if exclusions.excluded_unknown_breed > 0:
        parts.append(
            f"{exclusions.excluded_unknown_breed} przypadków wykluczono z analiz "
            f"rasowych z powodu nieznanej rasy (podsumowania według typu wrzodu nadal "
            f"mogą je obejmować, jeśli gatunek i typ wrzodu są znane)."
        )

    if result.dog_ulcer_types:
        top_dog_ulcer = result.dog_ulcer_types[0]
        parts.append(
            f"Wśród psów najliczniejszy typ wrzodu to {top_dog_ulcer.ulcer_label} "
            f"(n={top_dog_ulcer.count}, mediana "
            f"{format_optional_number(top_dog_ulcer.median_days)} dni)."
        )
    if result.cat_ulcer_types:
        top_cat_ulcer = result.cat_ulcer_types[0]
        parts.append(
            f"Wśród kotów najliczniejszy typ wrzodu to {top_cat_ulcer.ulcer_label} "
            f"(n={top_cat_ulcer.count}, mediana "
            f"{format_optional_number(top_cat_ulcer.median_days)} dni)."
        )

    if result.dog_breed_ulcer_rows:
        top_dog_cell = result.dog_breed_ulcer_rows[0]
        parts.append(
            f"Najliczniejsza para rasa×typ wrzodu u psów: {top_dog_cell.breed_label} — "
            f"{top_dog_cell.ulcer_label} (n={top_dog_cell.count}, mediana "
            f"{format_optional_number(top_dog_cell.median_days)} dni)."
        )
    if result.cat_breed_ulcer_rows:
        top_cat_cell = result.cat_breed_ulcer_rows[0]
        parts.append(
            f"Najliczniejsza para rasa×typ wrzodu u kotów: {top_cat_cell.breed_label} — "
            f"{top_cat_cell.ulcer_label} (n={top_cat_cell.count}, mediana "
            f"{format_optional_number(top_cat_cell.median_days)} dni)."
        )

    return " ".join(parts)


def build_descriptive_stats_block(
    result: UlcerBreedTreatmentDurationResult,
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
            ("Wykluczone — nieprawidłowy typ wrzodu (n)", str(exclusions.excluded_invalid_ulcer)),
            (
                f"Wykluczone — grupa rasa×typ wrzodu n<{MIN_DISPLAY_GROUP_SIZE} (n)",
                str(exclusions.excluded_below_min_n),
            ),
            ("Uwzględnione — znany gatunek i typ wrzodu (n)", str(exclusions.included_with_known_species)),
            ("Uwzględnione — znana rasa i typ wrzodu (n)", str(exclusions.included_with_known_breed)),
            (
                f"W tabelach rasa×typ wrzodu (n≥{MIN_DISPLAY_GROUP_SIZE}) (n)",
                str(exclusions.included_in_breed_ulcer_tables),
            ),
            ("Liczba typów wrzodu — psy (n)", str(len(result.dog_ulcer_types))),
            ("Liczba typów wrzodu — koty (n)", str(len(result.cat_ulcer_types))),
            ("Liczba par rasa×typ wrzodu — psy (n)", str(len(result.dog_breed_ulcer_rows))),
            ("Liczba par rasa×typ wrzodu — koty (n)", str(len(result.cat_breed_ulcer_rows))),
        ),
    )


def exclusions_table_block(
    result: UlcerBreedTreatmentDurationResult,
) -> ReportTableBlock:
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
            ("Nieprawidłowy typ wrzodu (terminal_ulcer_code)", str(exclusions.excluded_invalid_ulcer)),
            (
                f"Grupa rasa×typ wrzodu z n<{MIN_DISPLAY_GROUP_SIZE}",
                str(exclusions.excluded_below_min_n),
            ),
        ),
    )


def dog_ulcer_types_table_block(
    result: UlcerBreedTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia według typu wrzodu — psy",
        columns=("Typ wrzodu", *_DURATION_TABLE_COLUMNS[1:]),
        rows=tuple(
            (row.ulcer_label, *_duration_group_row_cells(row)[1:])
            for row in result.dog_ulcer_types
        ),
    )


def cat_ulcer_types_table_block(
    result: UlcerBreedTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Czas leczenia według typu wrzodu — koty",
        columns=("Typ wrzodu", *_DURATION_TABLE_COLUMNS[1:]),
        rows=tuple(
            (row.ulcer_label, *_duration_group_row_cells(row)[1:])
            for row in result.cat_ulcer_types
        ),
    )


def _breed_ulcer_row_cells(row: BreedUlcerDurationRow) -> tuple[str, ...]:
    return (
        row.breed_label,
        row.ulcer_label,
        str(row.count),
        format_optional_number(row.mean_days),
        format_optional_number(row.median_days),
        format_optional_number(row.min_days),
        format_optional_number(row.max_days),
        format_optional_number(row.percentile_25_days),
        format_optional_number(row.percentile_75_days),
    )


def dog_breed_ulcer_table_block(
    result: UlcerBreedTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Czas leczenia według rasy i typu wrzodu — psy "
            f"(tylko grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=_BREED_ULCER_TABLE_COLUMNS,
        rows=tuple(_breed_ulcer_row_cells(row) for row in result.dog_breed_ulcer_rows),
    )


def cat_breed_ulcer_table_block(
    result: UlcerBreedTreatmentDurationResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title=(
            f"Czas leczenia według rasy i typu wrzodu — koty "
            f"(tylko grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
        ),
        columns=_BREED_ULCER_TABLE_COLUMNS,
        rows=tuple(_breed_ulcer_row_cells(row) for row in result.cat_breed_ulcer_rows),
    )
