from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from data_sterilizer.schemas.clinical import (
    DATE_APPOINTMENT_COLUMN,
    PATIENT_ID_COLUMN as CLINICAL_PATIENT_ID_COLUMN,
    is_valid_clinical_date,
)
from data_sterilizer.schemas.micro import (
    BACTERIA_COLUMN,
    DATE_COLLECT_COLUMN,
    NEGATIVE_BACTERIA_VALUE,
    PATIENT_ID_COLUMN as MICRO_PATIENT_ID_COLUMN,
    RESULT_ID_COLUMN,
    parse_micro_date,
)

UNKNOWN_VALUE = "xxx"


@dataclass(frozen=True)
class BacteriaFrequencyRow:
    bacteria: str
    count: int
    percentage: float


@dataclass(frozen=True)
class MatchingSummary:
    clinical_rows: int
    matched_pairs: int
    unmatched_clinical_rows: int
    patients_with_multiple_results: int


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


def _resolve_column(clinical_or_micro: pd.DataFrame, *candidates: str) -> str | None:
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in clinical_or_micro.columns
    }
    for candidate in candidates:
        if candidate in clinical_or_micro.columns:
            return candidate
        actual = lower_to_actual.get(candidate.lower())
        if actual is not None:
            return actual
    return None


def _parse_clinical_date(value: object) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == UNKNOWN_VALUE:
        return None
    if not is_valid_clinical_date(text):
        return None
    day_text, month_text, year_text = text.split(".")
    return datetime(int(year_text), int(month_text), int(day_text))


def _normalize_bacteria(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().lower()
    if not text or text == UNKNOWN_VALUE:
        return None
    return text


def _match_micro_results_to_clinical(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
) -> tuple[pd.DataFrame, MatchingSummary]:
    """Match each clinical row to one micro result for the same patient.

    When a patient has multiple micro result_ID values, choose the result whose
    date_collect is closest to clinical.date_appointment_first_before_micro.
    All micro rows sharing the selected result_ID are kept for bacteria counting.
    """
    clinical_patient_col = _resolve_column(clinical, CLINICAL_PATIENT_ID_COLUMN)
    appointment_col = _resolve_column(clinical, DATE_APPOINTMENT_COLUMN)
    micro_patient_col = _resolve_column(micro, MICRO_PATIENT_ID_COLUMN)
    result_id_col = _resolve_column(micro, RESULT_ID_COLUMN)
    date_collect_col = _resolve_column(micro, DATE_COLLECT_COLUMN)
    bacteria_col = _resolve_column(micro, BACTERIA_COLUMN)

    if any(
        column is None
        for column in (
            clinical_patient_col,
            appointment_col,
            micro_patient_col,
            result_id_col,
            date_collect_col,
            bacteria_col,
        )
    ):
        return pd.DataFrame(), MatchingSummary(0, 0, 0, 0)

    clinical_work = clinical.copy()
    clinical_work["_appointment_date"] = clinical_work[appointment_col].map(
        _parse_clinical_date
    )

    micro_results = (
        micro.groupby([micro_patient_col, result_id_col], dropna=False)
        .agg({date_collect_col: "first"})
        .reset_index()
    )
    micro_results["_collect_date"] = micro_results[date_collect_col].map(parse_micro_date)
    micro_results = micro_results.dropna(subset=["_collect_date"])

    patients_with_multiple_results = int(
        micro_results.groupby(micro_patient_col)[result_id_col].nunique().gt(1).sum()
    )

    matched_rows: list[dict[str, object]] = []
    matched_clinical_rows = 0
    unmatched_clinical_rows = 0

    for clinical_index, clinical_row in clinical_work.iterrows():
        appointment_date = clinical_row["_appointment_date"]
        patient_id = clinical_row[clinical_patient_col]
        if appointment_date is None or pd.isna(patient_id):
            unmatched_clinical_rows += 1
            continue

        patient_micro = micro_results[micro_results[micro_patient_col] == patient_id]
        if patient_micro.empty:
            unmatched_clinical_rows += 1
            continue

        best_match = min(
            patient_micro.to_dict("records"),
            key=lambda row: (
                abs((row["_collect_date"] - appointment_date).days),
                row["_collect_date"],
                str(row[result_id_col]),
            ),
        )
        matched_result_id = best_match[result_id_col]
        matched_micro_rows = micro[
            (micro[micro_patient_col] == patient_id)
            & (micro[result_id_col] == matched_result_id)
        ]

        matched_clinical_rows += 1
        for _, micro_row in matched_micro_rows.iterrows():
            matched_rows.append(
                {
                    "clinical_index": clinical_index,
                    "patient_ID": patient_id,
                    "result_ID": matched_result_id,
                    "bacteria": micro_row[bacteria_col],
                }
            )

    matching = MatchingSummary(
        clinical_rows=len(clinical),
        matched_pairs=matched_clinical_rows,
        unmatched_clinical_rows=unmatched_clinical_rows,
        patients_with_multiple_results=patients_with_multiple_results,
    )
    if not matched_rows:
        return pd.DataFrame(), matching

    return pd.DataFrame(matched_rows), matching


def compute_microbiology_results(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_micro_label: str = "micro",
) -> MicrobiologyResultsResult:
    required_checks = {
        "clinical.patient_ID": _resolve_column(clinical, CLINICAL_PATIENT_ID_COLUMN),
        "clinical.date_appointment_first_before_micro": _resolve_column(
            clinical, DATE_APPOINTMENT_COLUMN
        ),
        "micro.patient_ID": _resolve_column(micro, MICRO_PATIENT_ID_COLUMN),
        "micro.result_ID": _resolve_column(micro, RESULT_ID_COLUMN),
        "micro.date_collect": _resolve_column(micro, DATE_COLLECT_COLUMN),
        "micro.bacteria": _resolve_column(micro, BACTERIA_COLUMN),
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

    matched_pairs, matching = _match_micro_results_to_clinical(clinical, micro)
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

    normalized_bacteria = matched_pairs["bacteria"].map(_normalize_bacteria)
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
