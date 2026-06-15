from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.patient import (
    DATE_OF_BIRTH_COLUMN,
    DISEASES_NOT_OPHT_COLUMN,
    GENDER_COLUMN,
    OTHER_DISEASES_OPHT_COLUMN,
    PATIENT_ID_COLUMN,
)
from vetstats_app.analysis.patient_id_cross_table_summary import normalize_patient_id

UNKNOWN_VALUE = "xxx"
UNKNOWN_LABEL = "nie wiadomo"

PATIENT_FIELD_LABELS: tuple[tuple[str, str], ...] = (
    (PATIENT_ID_COLUMN, "patient_ID"),
    ("name", "Imię"),
    (DATE_OF_BIRTH_COLUMN, "Data urodzenia"),
    ("species", "Gatunek"),
    ("breed", "Rasa"),
    (GENDER_COLUMN, "Płeć"),
    (DISEASES_NOT_OPHT_COLUMN, "Choroby poza okulistyką"),
    (OTHER_DISEASES_OPHT_COLUMN, "Inne choroby okulistyczne"),
)

CLINICAL_DISPLAY_COLUMNS: tuple[str, ...] = (
    "eye",
    "type_of_ulcer",
    "date_appointment_first_before_micro",
    "duration_of_problem",
    "farmacology_surgery",
    "topical_systemic",
    "type_of_surgery",
    "how_ended",
)

MICRO_DISPLAY_COLUMNS: tuple[str, ...] = (
    "result_ID",
    "date_collect",
    "date_result",
    "bacteria",
    "growth",
)


@dataclass(frozen=True)
class PatientListEntry:
    patient_id: str
    label: str


@dataclass(frozen=True)
class PatientFieldRow:
    field_name: str
    label: str
    value: str


@dataclass(frozen=True)
class PatientHistoryCatalog:
    source_labels: dict[str, str]
    patients: tuple[PatientListEntry, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


@dataclass(frozen=True)
class PatientHistoryDetail:
    patient_id: str
    patient_fields: tuple[PatientFieldRow, ...]
    clinical_columns: tuple[str, ...]
    clinical_rows: tuple[tuple[str, ...], ...]
    micro_columns: tuple[str, ...]
    micro_rows: tuple[tuple[str, ...], ...]
    summary: str


def format_display_value(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return UNKNOWN_LABEL

    text = str(value).strip()
    if not text or text.lower() == UNKNOWN_VALUE:
        return UNKNOWN_LABEL
    return text


def _resolve_column(frame: pd.DataFrame, column_name: str) -> str | None:
    if column_name in frame.columns:
        return column_name

    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    return lower_to_actual.get(column_name.lower())


def _build_patient_label(patient_id: str, row: pd.Series) -> str:
    name = format_display_value(row.get("name"))
    species = format_display_value(row.get("species"))
    if name == UNKNOWN_LABEL and species == UNKNOWN_LABEL:
        return patient_id
    if species == UNKNOWN_LABEL:
        return f"{patient_id} — {name}"
    return f"{patient_id} — {name} ({species})"


def build_patient_history_catalog(
    patient: pd.DataFrame,
    *,
    source_labels: dict[str, str] | None = None,
) -> PatientHistoryCatalog:
    source_labels = source_labels or {}
    patient_id_col = _resolve_column(patient, PATIENT_ID_COLUMN)
    if patient_id_col is None:
        return PatientHistoryCatalog(
            source_labels=source_labels,
            patients=(),
            error_message="Brak kolumny patient_ID w tabeli patient.",
        )

    entries: list[PatientListEntry] = []
    seen_ids: set[str] = set()
    for _, row in patient.iterrows():
        patient_id = normalize_patient_id(row[patient_id_col])
        if patient_id is None or patient_id in seen_ids:
            continue
        seen_ids.add(patient_id)
        entries.append(
            PatientListEntry(
                patient_id=patient_id,
                label=_build_patient_label(patient_id, row),
            )
        )

    entries.sort(key=lambda entry: entry.label.lower())
    return PatientHistoryCatalog(
        source_labels=source_labels,
        patients=tuple(entries),
    )


def _matches_normalized_patient_id(value: object, normalized_id: str) -> bool:
    return normalize_patient_id(value) == normalized_id


def _rows_for_table(
    frame: pd.DataFrame,
    *,
    patient_id: str,
    columns: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    patient_id_col = _resolve_column(frame, "patient_ID")
    if patient_id_col is None:
        return (), ()

    available_columns = tuple(
        column for column in columns if _resolve_column(frame, column) is not None
    )
    if not available_columns:
        return (), ()

    matched = frame[
        frame[patient_id_col].map(
            lambda value: _matches_normalized_patient_id(value, patient_id)
        )
    ]
    rows: list[tuple[str, ...]] = []
    for _, row in matched.iterrows():
        rows.append(
            tuple(
                format_display_value(row[_resolve_column(frame, column)])
                for column in available_columns
            )
        )

    return available_columns, tuple(rows)


def build_patient_history_detail(
    patient_id: str,
    patient: pd.DataFrame,
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
) -> PatientHistoryDetail | None:
    normalized_id = normalize_patient_id(patient_id)
    if normalized_id is None:
        return None

    patient_id_col = _resolve_column(patient, PATIENT_ID_COLUMN)
    if patient_id_col is None:
        return None

    patient_rows = patient[
        patient[patient_id_col].map(
            lambda value: _matches_normalized_patient_id(value, normalized_id)
        )
    ]
    if patient_rows.empty:
        return None

    patient_row = patient_rows.iloc[0]
    patient_fields: list[PatientFieldRow] = []
    for field_name, label in PATIENT_FIELD_LABELS:
        if field_name not in patient_row.index and _resolve_column(patient, field_name) is None:
            continue
        column = field_name if field_name in patient_row.index else _resolve_column(patient, field_name)
        patient_fields.append(
            PatientFieldRow(
                field_name=field_name,
                label=label,
                value=format_display_value(patient_row[column]),
            )
        )

    clinical_columns, clinical_rows = _rows_for_table(
        clinical,
        patient_id=normalized_id,
        columns=CLINICAL_DISPLAY_COLUMNS,
    )
    micro_columns, micro_rows = _rows_for_table(
        micro,
        patient_id=normalized_id,
        columns=MICRO_DISPLAY_COLUMNS,
    )

    summary = (
        f"Historia indywidualna pacjenta {normalized_id}: "
        f"{len(clinical_rows)} wierszy clinical, {len(micro_rows)} wierszy micro."
    )

    return PatientHistoryDetail(
        patient_id=normalized_id,
        patient_fields=tuple(patient_fields),
        clinical_columns=clinical_columns,
        clinical_rows=clinical_rows,
        micro_columns=micro_columns,
        micro_rows=micro_rows,
        summary=summary,
    )
