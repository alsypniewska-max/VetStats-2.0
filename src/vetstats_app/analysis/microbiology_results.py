from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.clinical import (
    DATE_APPOINTMENT_COLUMN,
    PATIENT_ID_COLUMN as CLINICAL_PATIENT_ID_COLUMN,
)
from data_sterilizer.schemas.micro import (
    BACTERIA_COLUMN,
    DATE_COLLECT_COLUMN,
    NEGATIVE_BACTERIA_VALUE,
    PATIENT_ID_COLUMN as MICRO_PATIENT_ID_COLUMN,
    RESULT_ID_COLUMN,
)
from vetstats_app.analysis.clinical_common import resolve_column
from vetstats_app.analysis.clinical_micro_matching import (
    ClinicalMicroMatchingSummary,
    match_clinical_rows_to_micro_bacteria,
    normalize_micro_bacteria,
)
from vetstats_app.analysis.report_models import ReportTableBlock

MatchingSummary = ClinicalMicroMatchingSummary


@dataclass(frozen=True)
class BacteriaFrequencyRow:
    bacteria: str
    count: int
    percentage: float


@dataclass(frozen=True)
class MicrobiologyResultsResult:
    source_clinical_label: str
    source_micro_label: str
    matching: MatchingSummary
    bacteria_frequencies: tuple[BacteriaFrequencyRow, ...]
    negative_count: int
    negative_percentage: float
    included_isolates: int
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def compute_microbiology_results(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_micro_label: str = "micro",
) -> MicrobiologyResultsResult:
    required_checks = {
        "clinical.patient_ID": resolve_column(clinical, CLINICAL_PATIENT_ID_COLUMN),
        "clinical.date_appointment_first_before_micro": resolve_column(
            clinical, DATE_APPOINTMENT_COLUMN
        ),
        "micro.patient_ID": resolve_column(micro, MICRO_PATIENT_ID_COLUMN),
        "micro.result_ID": resolve_column(micro, RESULT_ID_COLUMN),
        "micro.date_collect": resolve_column(micro, DATE_COLLECT_COLUMN),
        "micro.bacteria": resolve_column(micro, BACTERIA_COLUMN),
    }
    missing = [name for name, column in required_checks.items() if column is None]
    if missing:
        return MicrobiologyResultsResult(
            source_clinical_label=source_clinical_label,
            source_micro_label=source_micro_label,
            matching=MatchingSummary(0, 0, 0, 0),
            bacteria_frequencies=(),
            negative_count=0,
            negative_percentage=0.0,
            included_isolates=0,
            error_message=(
                "Brak wymaganych kolumn do analizy mikrobiologicznej: "
                + ", ".join(missing)
                + "."
            ),
        )

    matched_pairs, matching = match_clinical_rows_to_micro_bacteria(clinical, micro)
    if matched_pairs.empty:
        return MicrobiologyResultsResult(
            source_clinical_label=source_clinical_label,
            source_micro_label=source_micro_label,
            matching=matching,
            bacteria_frequencies=(),
            negative_count=0,
            negative_percentage=0.0,
            included_isolates=0,
        )

    normalized_bacteria = matched_pairs["bacteria"].map(normalize_micro_bacteria)
    valid_mask = normalized_bacteria.notna()
    valid_bacteria = normalized_bacteria[valid_mask]

    negative_count = int((valid_bacteria == NEGATIVE_BACTERIA_VALUE).sum())
    positive_bacteria = valid_bacteria[valid_bacteria != NEGATIVE_BACTERIA_VALUE]
    included_isolates = len(positive_bacteria)

    counts = positive_bacteria.value_counts()
    frequencies: list[BacteriaFrequencyRow] = []
    for bacteria, count in counts.items():
        percentage = (count / included_isolates * 100.0) if included_isolates else 0.0
        frequencies.append(
            BacteriaFrequencyRow(
                bacteria=str(bacteria),
                count=int(count),
                percentage=percentage,
            )
        )
    frequencies.sort(key=lambda row: (-row.count, row.bacteria))

    valid_total = len(valid_bacteria)
    negative_percentage = negative_count / valid_total * 100.0 if valid_total else 0.0

    return MicrobiologyResultsResult(
        source_clinical_label=source_clinical_label,
        source_micro_label=source_micro_label,
        matching=matching,
        bacteria_frequencies=tuple(frequencies),
        negative_count=negative_count,
        negative_percentage=negative_percentage,
        included_isolates=included_isolates,
    )


def build_summary_details(result: MicrobiologyResultsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych clinical/micro."

    matching = result.matching
    return (
        f"Źródła danych: {result.source_clinical_label}, {result.source_micro_label}. "
        f"Dopasowano {matching.matched_pairs} z {matching.clinical_rows} wierszy clinical "
        f"do wyników mikrobiologicznych."
    )


def build_matching_details(result: MicrobiologyResultsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się dopasować wyników mikrobiologicznych."

    matching = result.matching
    return (
        f"Pacjenci z wieloma result_ID: {matching.patients_with_multiple_results}. "
        f"Niedopasowane wiersze clinical: {matching.unmatched_clinical_rows}. "
        "Dla każdego wiersza clinical wybierany jest result_ID z date_collect "
        "najbliższym date_appointment_first_before_micro."
    )


def build_interpretation_summary(result: MicrobiologyResultsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się obliczyć wyników mikrobiologicznych."

    if result.matching.matched_pairs == 0:
        return "Brak dopasowanych par clinical–micro do analizy."

    parts = [
        (
            f"Przeanalizowano {result.matching.matched_pairs} dopasowanych przypadków. "
            f"Wyniki negatywne: {result.negative_count} "
            f"({result.negative_percentage:.1f}% ważnych obserwacji bakteryjnych)."
        )
    ]

    if result.bacteria_frequencies:
        most_common = result.bacteria_frequencies[0]
        parts.append(
            f"Najczęściej izolowana bakteria: {most_common.bacteria} "
            f"({most_common.count}, {most_common.percentage:.1f}%)."
        )
    else:
        parts.append("Brak dodatnich izolacji bakteryjnych w dopasowanych wynikach.")

    return " ".join(parts)


def build_descriptive_stats_block(
    result: MicrobiologyResultsResult,
) -> ReportTableBlock:
    matching = result.matching
    clinical_rows = matching.clinical_rows
    matched_pairs = matching.matched_pairs
    unmatched_rows = matching.unmatched_clinical_rows
    matched_pct = (matched_pairs / clinical_rows * 100.0) if clinical_rows else 0.0
    unmatched_pct = (unmatched_rows / clinical_rows * 100.0) if clinical_rows else 0.0

    valid_observations = result.negative_count + result.included_isolates
    bacteria_categories = len(result.bacteria_frequencies)

    if result.bacteria_frequencies:
        most_common = result.bacteria_frequencies[0]
        most_common_bacteria = most_common.bacteria
        most_common_count = str(most_common.count)
        most_common_percentage = f"{most_common.percentage:.1f}"
    else:
        most_common_bacteria = "—"
        most_common_count = "0"
        most_common_percentage = "0.0"

    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba wierszy clinical (N)", str(clinical_rows)),
            ("Dopasowane pary clinical–micro (n)", str(matched_pairs)),
            ("Niedopasowane wiersze clinical (n)", str(unmatched_rows)),
            ("Dopasowane (%)", f"{matched_pct:.1f}"),
            ("Niedopasowane (%)", f"{unmatched_pct:.1f}"),
            (
                "Pacjenci z wieloma result_ID (n)",
                str(matching.patients_with_multiple_results),
            ),
            ("Ważne obserwacje bakteryjne (n)", str(valid_observations)),
            ("Dodatnie izolacje (n)", str(result.included_isolates)),
            ("Wyniki negatywne (n)", str(result.negative_count)),
            ("Wyniki negatywne (%)", f"{result.negative_percentage:.1f}"),
            ("Liczba izolowanych bakterii (kategorie)", str(bacteria_categories)),
            ("Najczęstsza bakteria", most_common_bacteria),
            ("Liczba — najczęstsza bakteria", most_common_count),
            ("Udział (%) — najczęstsza bakteria", most_common_percentage),
        ),
    )
