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
from vetstats_app.analysis.clinical_common import resolve_column
from vetstats_app.analysis.display_text import sanitize_matplotlib_text

UNKNOWN_VALUE = "xxx"


@dataclass(frozen=True)
class ClinicalMicroMatchingSummary:
    clinical_rows: int
    matched_pairs: int
    unmatched_clinical_rows: int
    patients_with_multiple_results: int


def parse_clinical_appointment_datetime(value: object) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == UNKNOWN_VALUE:
        return None
    if not is_valid_clinical_date(text):
        return None
    day_text, month_text, year_text = text.split(".")
    return datetime(int(year_text), int(month_text), int(day_text))


def normalize_micro_bacteria(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = sanitize_matplotlib_text(str(value).strip().lower())
    if not text or text == UNKNOWN_VALUE:
        return None
    return text


def match_clinical_rows_to_micro_bacteria(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
) -> tuple[pd.DataFrame, ClinicalMicroMatchingSummary]:
    """Match each clinical row to one micro result for the same patient.

    When a patient has multiple micro result_ID values, choose the result whose
    date_collect is closest to clinical.date_appointment_first_before_micro.
    All micro rows sharing the selected result_ID are returned for bacteria analysis.
    """
    clinical_patient_col = resolve_column(clinical, CLINICAL_PATIENT_ID_COLUMN)
    appointment_col = resolve_column(clinical, DATE_APPOINTMENT_COLUMN)
    micro_patient_col = resolve_column(micro, MICRO_PATIENT_ID_COLUMN)
    result_id_col = resolve_column(micro, RESULT_ID_COLUMN)
    date_collect_col = resolve_column(micro, DATE_COLLECT_COLUMN)
    bacteria_col = resolve_column(micro, BACTERIA_COLUMN)

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
        return pd.DataFrame(), ClinicalMicroMatchingSummary(0, 0, 0, 0)

    clinical_work = clinical.copy()
    clinical_work["_appointment_date"] = clinical_work[appointment_col].map(
        parse_clinical_appointment_datetime
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

    matching = ClinicalMicroMatchingSummary(
        clinical_rows=len(clinical),
        matched_pairs=matched_clinical_rows,
        unmatched_clinical_rows=unmatched_clinical_rows,
        patients_with_multiple_results=patients_with_multiple_results,
    )
    if not matched_rows:
        return pd.DataFrame(), matching

    return pd.DataFrame(matched_rows), matching
