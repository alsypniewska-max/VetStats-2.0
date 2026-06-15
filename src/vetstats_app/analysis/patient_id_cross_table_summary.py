from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_sterilizer.schemas.clinical import PATIENT_ID_COLUMN as CLINICAL_PATIENT_ID_COLUMN
from data_sterilizer.schemas.micro import PATIENT_ID_COLUMN as MICRO_PATIENT_ID_COLUMN
from data_sterilizer.schemas.patient import PATIENT_ID_COLUMN as PATIENT_PATIENT_ID_COLUMN

UNKNOWN_VALUE = "xxx"

TABLE_ORDER: tuple[str, ...] = ("patient", "clinical", "micro")
TABLE_PATIENT_COLUMNS: dict[str, str] = {
    "patient": PATIENT_PATIENT_ID_COLUMN,
    "clinical": CLINICAL_PATIENT_ID_COLUMN,
    "micro": MICRO_PATIENT_ID_COLUMN,
}


@dataclass(frozen=True)
class TablePatientIdSummary:
    table_name: str
    source_label: str
    total_rows: int
    unique_patient_ids: int
    excluded_rows: int


@dataclass(frozen=True)
class PairwisePatientIdLinkage:
    table_a: str
    table_b: str
    shared_count: int
    only_in_a: int
    only_in_b: int


@dataclass(frozen=True)
class SingleTableOnlyPatientIds:
    table_name: str
    count: int


@dataclass(frozen=True)
class PatientIdCrossTableSummaryResult:
    tables: tuple[TablePatientIdSummary, ...]
    pairwise: tuple[PairwisePatientIdLinkage, ...]
    in_all_three: int
    only_in_single_table: tuple[SingleTableOnlyPatientIds, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _resolve_column(frame: pd.DataFrame, column_name: str) -> str | None:
    if column_name in frame.columns:
        return column_name

    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in frame.columns
    }
    return lower_to_actual.get(column_name.lower())


def normalize_patient_id(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    text = str(value).strip()
    if not text or text.lower() == UNKNOWN_VALUE:
        return None
    return text


def _extract_valid_patient_ids(
    frame: pd.DataFrame,
    *,
    table_name: str,
) -> tuple[set[str], int, int]:
    column_name = TABLE_PATIENT_COLUMNS[table_name]
    column = _resolve_column(frame, column_name)
    if column is None:
        return set(), len(frame), len(frame)

    valid_ids: set[str] = set()
    excluded_rows = 0
    for value in frame[column].tolist():
        patient_id = normalize_patient_id(value)
        if patient_id is None:
            excluded_rows += 1
            continue
        valid_ids.add(patient_id)

    return valid_ids, len(frame), excluded_rows


def _pairwise_linkage(
    table_a: str,
    ids_a: set[str],
    table_b: str,
    ids_b: set[str],
) -> PairwisePatientIdLinkage:
    shared = ids_a & ids_b
    return PairwisePatientIdLinkage(
        table_a=table_a,
        table_b=table_b,
        shared_count=len(shared),
        only_in_a=len(ids_a - ids_b),
        only_in_b=len(ids_b - ids_a),
    )


def compute_patient_id_cross_table_summary(
    datasets: dict[str, pd.DataFrame],
    *,
    source_labels: dict[str, str] | None = None,
) -> PatientIdCrossTableSummaryResult:
    source_labels = source_labels or {}
    missing_tables = [name for name in TABLE_ORDER if name not in datasets]
    if missing_tables:
        return PatientIdCrossTableSummaryResult(
            tables=(),
            pairwise=(),
            in_all_three=0,
            only_in_single_table=(),
            error_message=(
                "Brak wymaganych tabel: " + ", ".join(missing_tables) + "."
            ),
        )

    id_sets: dict[str, set[str]] = {}
    table_summaries: list[TablePatientIdSummary] = []

    for table_name in TABLE_ORDER:
        frame = datasets[table_name]
        patient_ids, total_rows, excluded_rows = _extract_valid_patient_ids(
            frame,
            table_name=table_name,
        )
        id_sets[table_name] = patient_ids
        table_summaries.append(
            TablePatientIdSummary(
                table_name=table_name,
                source_label=source_labels.get(table_name, table_name),
                total_rows=total_rows,
                unique_patient_ids=len(patient_ids),
                excluded_rows=excluded_rows,
            )
        )

    pairwise = (
        _pairwise_linkage("patient", id_sets["patient"], "clinical", id_sets["clinical"]),
        _pairwise_linkage("patient", id_sets["patient"], "micro", id_sets["micro"]),
        _pairwise_linkage("clinical", id_sets["clinical"], "micro", id_sets["micro"]),
    )

    in_all_three = len(
        id_sets["patient"] & id_sets["clinical"] & id_sets["micro"]
    )

    only_in_single_table = (
        SingleTableOnlyPatientIds(
            table_name="patient",
            count=len(
                id_sets["patient"]
                - id_sets["clinical"]
                - id_sets["micro"]
            ),
        ),
        SingleTableOnlyPatientIds(
            table_name="clinical",
            count=len(
                id_sets["clinical"]
                - id_sets["patient"]
                - id_sets["micro"]
            ),
        ),
        SingleTableOnlyPatientIds(
            table_name="micro",
            count=len(
                id_sets["micro"]
                - id_sets["patient"]
                - id_sets["clinical"]
            ),
        ),
    )

    return PatientIdCrossTableSummaryResult(
        tables=tuple(table_summaries),
        pairwise=pairwise,
        in_all_three=in_all_three,
        only_in_single_table=only_in_single_table,
    )


def build_summary_details(result: PatientIdCrossTableSummaryResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się wczytać danych."

    labels = ", ".join(table.source_label for table in result.tables)
    return (
        "Automatyczne podsumowanie powiązań między tabelami po patient_ID. "
        f"Źródła danych: {labels}. "
        "Wykluczono wiersze z pustym, xxx lub nieprawidłowym patient_ID."
    )


def build_interpretation_summary(
    result: PatientIdCrossTableSummaryResult,
) -> str:
    if not result.is_success:
        return (
            result.error_message
            or "Nie udało się obliczyć podsumowania powiązań patient_ID."
        )

    if not result.tables:
        return "Brak tabel do analizy powiązań patient_ID."

    parts = [
        (
            f"patient_ID występuje we wszystkich trzech tabelach dla "
            f"{result.in_all_three} identyfikatorów."
        )
    ]

    for linkage in result.pairwise:
        parts.append(
            f"{linkage.table_a}–{linkage.table_b}: wspólne {linkage.shared_count}, "
            f"tylko w {linkage.table_a} {linkage.only_in_a}, "
            f"tylko w {linkage.table_b} {linkage.only_in_b}."
        )

    single_only = [
        entry for entry in result.only_in_single_table if entry.count > 0
    ]
    if single_only:
        single_text = ", ".join(
            f"{entry.table_name} ({entry.count})" for entry in single_only
        )
        parts.append(
            f"Identyfikatory obecne wyłącznie w jednej tabeli: {single_text}."
        )

    return " ".join(parts)
