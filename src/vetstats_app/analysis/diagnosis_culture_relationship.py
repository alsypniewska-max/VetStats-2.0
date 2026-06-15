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
    PATIENT_ID_COLUMN as MICRO_PATIENT_ID_COLUMN,
    RESULT_ID_COLUMN,
    parse_micro_date,
)
from vetstats_app.analysis.diagnosis_frequency import (
    DIAGNOSIS_CODE_MAPPING,
    DIAGNOSIS_LABELS,
    TYPE_OF_ULCER_COLUMN,
    normalize_ulcer_code,
)

UNKNOWN_VALUE = "xxx"


@dataclass(frozen=True)
class CategoryBacteriaRow:
    bacteria: str
    count: int


@dataclass(frozen=True)
class UlcerCategoryCultureSummary:
    code: str
    label: str
    matched_cases: int
    bacteria_rows: tuple[CategoryBacteriaRow, ...]


@dataclass(frozen=True)
class MatchingSummary:
    clinical_rows: int
    matched_pairs: int
    unmatched_clinical_rows: int
    patients_with_multiple_results: int
    excluded_invalid_ulcer: int


@dataclass(frozen=True)
class DiagnosisCultureRelationshipResult:
    source_clinical_label: str
    source_micro_label: str
    matching: MatchingSummary
    categories: tuple[UlcerCategoryCultureSummary, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _resolve_column(frame: pd.DataFrame, *candidates: str) -> str | None:
    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    for candidate in candidates:
        if candidate in frame.columns:
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


def _match_clinical_micro_pairs(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
) -> tuple[pd.DataFrame, MatchingSummary]:
    """Match each clinical row to one micro result for the same patient.

    When a patient has multiple micro result_ID values, choose the result whose
    date_collect is closest to clinical.date_appointment_first_before_micro.
    """
    clinical_patient_col = _resolve_column(clinical, CLINICAL_PATIENT_ID_COLUMN)
    appointment_col = _resolve_column(clinical, DATE_APPOINTMENT_COLUMN)
    ulcer_col = _resolve_column(clinical, TYPE_OF_ULCER_COLUMN)
    micro_patient_col = _resolve_column(micro, MICRO_PATIENT_ID_COLUMN)
    result_id_col = _resolve_column(micro, RESULT_ID_COLUMN)
    date_collect_col = _resolve_column(micro, DATE_COLLECT_COLUMN)
    bacteria_col = _resolve_column(micro, BACTERIA_COLUMN)

    if any(
        column is None
        for column in (
            clinical_patient_col,
            appointment_col,
            ulcer_col,
            micro_patient_col,
            result_id_col,
            date_collect_col,
            bacteria_col,
        )
    ):
        return pd.DataFrame(), MatchingSummary(0, 0, 0, 0, 0)

    clinical_work = clinical.copy()
    clinical_work["_appointment_date"] = clinical_work[appointment_col].map(
        _parse_clinical_date
    )
    clinical_work["_ulcer_code"] = clinical_work[ulcer_col].map(normalize_ulcer_code)

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
    excluded_invalid_ulcer = 0

    for clinical_index, clinical_row in clinical_work.iterrows():
        appointment_date = clinical_row["_appointment_date"]
        patient_id = clinical_row[clinical_patient_col]
        ulcer_code = clinical_row["_ulcer_code"]

        if appointment_date is None or pd.isna(patient_id):
            unmatched_clinical_rows += 1
            continue

        if ulcer_code is None or pd.isna(ulcer_code):
            excluded_invalid_ulcer += 1
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
                    "ulcer_code": ulcer_code,
                    "ulcer_label": DIAGNOSIS_LABELS[str(ulcer_code)],
                    "result_ID": matched_result_id,
                    "bacteria": micro_row[bacteria_col],
                }
            )

    matching = MatchingSummary(
        clinical_rows=len(clinical),
        matched_pairs=matched_clinical_rows,
        unmatched_clinical_rows=unmatched_clinical_rows,
        patients_with_multiple_results=patients_with_multiple_results,
        excluded_invalid_ulcer=excluded_invalid_ulcer,
    )
    if not matched_rows:
        return pd.DataFrame(), matching

    return pd.DataFrame(matched_rows), matching


def compute_diagnosis_culture_relationship(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_micro_label: str = "micro",
) -> DiagnosisCultureRelationshipResult:
    ulcer_col = _resolve_column(clinical, TYPE_OF_ULCER_COLUMN)
    if ulcer_col is None:
        return DiagnosisCultureRelationshipResult(
            source_clinical_label=source_clinical_label,
            source_micro_label=source_micro_label,
            matching=MatchingSummary(0, 0, 0, 0, 0),
            categories=(),
            error_message="Brak kolumny type_of_ulcer w tabeli clinical.",
        )

    matched_pairs, matching = _match_clinical_micro_pairs(clinical, micro)
    if matched_pairs.empty:
        return DiagnosisCultureRelationshipResult(
            source_clinical_label=source_clinical_label,
            source_micro_label=source_micro_label,
            matching=matching,
            categories=(),
        )

    matched_pairs = matched_pairs.copy()
    matched_pairs["_bacteria"] = matched_pairs["bacteria"].map(_normalize_bacteria)

    categories: list[UlcerCategoryCultureSummary] = []
    for code, label in DIAGNOSIS_CODE_MAPPING:
        category_rows = matched_pairs[matched_pairs["ulcer_code"] == code]
        matched_cases = int(category_rows["clinical_index"].nunique())

        valid_bacteria = category_rows["_bacteria"].dropna()
        bacteria_counts = valid_bacteria.value_counts()
        bacteria_rows = tuple(
            CategoryBacteriaRow(bacteria=str(bacteria), count=int(count))
            for bacteria, count in bacteria_counts.items()
        )
        bacteria_rows = tuple(sorted(bacteria_rows, key=lambda row: (-row.count, row.bacteria)))

        categories.append(
            UlcerCategoryCultureSummary(
                code=code,
                label=label,
                matched_cases=matched_cases,
                bacteria_rows=bacteria_rows,
            )
        )

    return DiagnosisCultureRelationshipResult(
        source_clinical_label=source_clinical_label,
        source_micro_label=source_micro_label,
        matching=matching,
        categories=tuple(categories),
    )


def build_summary_details(result: DiagnosisCultureRelationshipResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych clinical/micro."

    matching = result.matching
    return (
        f"Źródła danych: {result.source_clinical_label}, {result.source_micro_label}. "
        f"Dopasowano {matching.matched_pairs} par clinical–micro z prawidłowym "
        f"type_of_ulcer (wykluczono {matching.excluded_invalid_ulcer} wierszy "
        f"z nieprawidłowym lub brakującym kodem wrzodu)."
    )


def build_matching_details(result: DiagnosisCultureRelationshipResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się dopasować wyników."

    matching = result.matching
    return (
        f"Pacjenci z wieloma result_ID: {matching.patients_with_multiple_results}. "
        f"Niedopasowane wiersze clinical: {matching.unmatched_clinical_rows}. "
        "Dla każdego wiersza clinical wybierany jest result_ID z date_collect "
        "najbliższym date_appointment_first_before_micro."
    )


def build_interpretation_summary(result: DiagnosisCultureRelationshipResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się obliczyć powiązania rozpoznań z posiewem."

    if result.matching.matched_pairs == 0:
        return "Brak dopasowanych par clinical–micro z prawidłowym type_of_ulcer."

    observed = [category for category in result.categories if category.matched_cases > 0]
    if not observed:
        return "Brak kategorii wrzodu z dopasowanymi przypadkami."

    largest = max(observed, key=lambda category: category.matched_cases)
    parts = [
        (
            f"Największa grupa: {largest.label} ({largest.matched_cases} dopasowanych przypadków)."
        )
    ]

    for category in observed:
        if category.bacteria_rows:
            top_bacteria = category.bacteria_rows[0]
            parts.append(
                f"{category.label}: najczęściej {top_bacteria.bacteria} "
                f"({top_bacteria.count})."
            )

    return " ".join(parts)
