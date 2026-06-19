from __future__ import annotations

import calendar
from collections.abc import Hashable, Iterator
from dataclasses import dataclass
from datetime import date

import pandas as pd

from data_sterilizer.schemas.clinical import PATIENT_ID_COLUMN
from vetstats_app.analysis.clinical_common import (
    format_display_value,
    normalize_ulcer_code,
    parse_clinical_dmy_date,
    resolve_column,
)
from vetstats_app.analysis.patient_id_cross_table_summary import normalize_patient_id

DATE_LAST_APPOINTMENT_COLUMN = "date_last_appointment"
TREATMENT_DURATION_DISPLAY_COLUMN = "czas_leczenia"
TREATMENT_DURATION_CONTINUED = "Leczenie kontynuowane"
TREATMENT_DURATION_NO_FOLLOWUP = (
    "Nie znany, pacjent nie pojawił się na kontrolach"
)
TREATMENT_DURATION_UNAVAILABLE = (
    "nie można obliczyć — brak danych o ostatniej wizycie"
)

HOW_ENDED_GOOD = "good"
HOW_ENDED_ENUCLEATION = "enucleation"
HOW_ENDED_NO_FOLLOWUP = "no followup"
HOW_ENDED_CONTINUATION = "continuation"


@dataclass(frozen=True)
class TreatmentCaseRecord:
    patient_id: str
    eye: str
    terminal_status: str | None
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    terminal_row_index: Hashable
    row_indices: tuple[Hashable, ...]
    terminal_ulcer_code: str | None


@dataclass(frozen=True)
class HealedCaseWithDuration:
    patient_id: str
    eye: str
    duration_days: int
    terminal_ulcer_code: str | None
    terminal_row_index: Hashable


@dataclass(frozen=True)
class TreatmentCaseExclusionSummary:
    total_clinical_rows: int
    excluded_non_ulcer: int
    excluded_not_good: int
    excluded_enucleation: int
    excluded_no_followup: int
    excluded_continuation: int
    excluded_duration_unavailable: int
    included_healed_with_duration: int


@dataclass(frozen=True)
class _ClinicalCaseRow:
    row_index: Hashable
    patient_id: str
    eye: str
    appointment_date: date | None
    how_ended: str | None
    last_appointment_date: date | None
    ulcer_code: str | None


@dataclass(frozen=True)
class _ClosedCase:
    case_rows: tuple[_ClinicalCaseRow, ...]
    terminal_status: str | None


def _normalize_how_ended_code(value: object) -> str | None:
    text = format_display_value(value)
    if text == "nie wiadomo":
        return None
    return text.lower()


def _normalize_eye_code(value: object) -> str | None:
    text = format_display_value(value)
    if text == "nie wiadomo":
        return None
    return text.lower()


def _polish_plural(count: int, one: str, few: str, many: str) -> str:
    count = abs(count)
    if count == 1:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def _add_calendar_month(value: date) -> date:
    month = value.month + 1
    year = value.year
    if month > 12:
        month = 1
        year += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(value.day, last_day))


def _decompose_calendar_duration(start: date, end: date) -> tuple[int, int, int]:
    if end < start:
        raise ValueError("end before start")
    total_days = (end - start).days
    months = 0
    cursor = start
    while True:
        next_anchor = _add_calendar_month(cursor)
        if next_anchor > end:
            break
        months += 1
        cursor = next_anchor
    remainder_days = (end - cursor).days
    return months, remainder_days, total_days


def _format_months_days_total(months: int, days: int, total_days: int) -> str:
    parts: list[str] = []
    if months > 0:
        parts.append(
            f"{months} {_polish_plural(months, 'miesiąc', 'miesiące', 'miesięcy')}"
        )
    if days > 0 or months == 0:
        parts.append(f"{days} {_polish_plural(days, 'dzień', 'dni', 'dni')}")
    body = ", ".join(parts)
    return (
        f"{body} ({total_days} {_polish_plural(total_days, 'dzień', 'dni', 'dni')})"
    )


def format_treatment_duration_text(
    *,
    terminal_status: str | None,
    is_intermediate_continuation: bool,
    start_date: date | None,
    end_date: date | None,
) -> str:
    if is_intermediate_continuation:
        return TREATMENT_DURATION_CONTINUED

    if terminal_status == HOW_ENDED_NO_FOLLOWUP:
        return TREATMENT_DURATION_NO_FOLLOWUP

    if terminal_status == HOW_ENDED_CONTINUATION:
        return TREATMENT_DURATION_CONTINUED

    if terminal_status in {HOW_ENDED_GOOD, HOW_ENDED_ENUCLEATION}:
        if start_date is None or end_date is None:
            return TREATMENT_DURATION_UNAVAILABLE
        try:
            months, days, total = _decompose_calendar_duration(start_date, end_date)
        except ValueError:
            return TREATMENT_DURATION_UNAVAILABLE
        base = _format_months_days_total(months, days, total)
        if terminal_status == HOW_ENDED_ENUCLEATION:
            return f"{base} (oko usunięto)"
        return base

    return TREATMENT_DURATION_UNAVAILABLE


def _clinical_case_row_from_series(
    row_index: Hashable,
    row: pd.Series,
    *,
    patient_id: str,
    eye_column: str | None,
    appointment_column: str | None,
    how_ended_column: str | None,
    last_appointment_column: str | None,
    ulcer_column: str | None,
) -> _ClinicalCaseRow | None:
    if eye_column is None:
        return None
    eye = _normalize_eye_code(row[eye_column])
    if eye is None:
        return None

    appointment_date = (
        parse_clinical_dmy_date(row[appointment_column])
        if appointment_column is not None
        else None
    )
    how_ended = (
        _normalize_how_ended_code(row[how_ended_column])
        if how_ended_column is not None
        else None
    )
    last_appointment_date = (
        parse_clinical_dmy_date(row[last_appointment_column])
        if last_appointment_column is not None
        else None
    )
    ulcer_code = (
        normalize_ulcer_code(row[ulcer_column])
        if ulcer_column is not None
        else None
    )
    return _ClinicalCaseRow(
        row_index=row_index,
        patient_id=patient_id,
        eye=eye,
        appointment_date=appointment_date,
        how_ended=how_ended,
        last_appointment_date=last_appointment_date,
        ulcer_code=ulcer_code,
    )


def _sort_case_rows(rows: list[_ClinicalCaseRow]) -> list[_ClinicalCaseRow]:
    return sorted(
        rows,
        key=lambda row: (
            row.appointment_date is None,
            row.appointment_date or date.max,
            str(row.row_index),
        ),
    )


def _find_continuation_successor_index(
    sorted_rows: list[_ClinicalCaseRow],
    current_index: int,
) -> int | None:
    current = sorted_rows[current_index]
    if current.appointment_date is None:
        return None
    for candidate_index in range(current_index + 1, len(sorted_rows)):
        candidate = sorted_rows[candidate_index]
        if candidate.appointment_date is None:
            continue
        if candidate.appointment_date > current.appointment_date:
            return candidate_index
    return None


def _close_duration_case(
    duration_by_row: dict[Hashable, str],
    case_rows: list[_ClinicalCaseRow],
    *,
    terminal_status: str | None,
) -> None:
    if not case_rows:
        return
    for case_row in case_rows[:-1]:
        if case_row.how_ended == HOW_ENDED_CONTINUATION:
            duration_by_row[case_row.row_index] = TREATMENT_DURATION_CONTINUED

    terminal_row = case_rows[-1]
    end_date: date | None = None
    if terminal_status in {HOW_ENDED_GOOD, HOW_ENDED_ENUCLEATION}:
        end_date = terminal_row.last_appointment_date
    duration_by_row[terminal_row.row_index] = format_treatment_duration_text(
        terminal_status=terminal_status,
        is_intermediate_continuation=False,
        start_date=case_rows[0].appointment_date,
        end_date=end_date,
    )


def _iter_closed_cases(sorted_rows: list[_ClinicalCaseRow]) -> Iterator[_ClosedCase]:
    current_case: list[_ClinicalCaseRow] = []
    start_new_case = True

    for row_index, case_row in enumerate(sorted_rows):
        if start_new_case:
            current_case = []
            start_new_case = False

        current_case.append(case_row)
        status = case_row.how_ended

        if status == HOW_ENDED_CONTINUATION:
            successor_index = _find_continuation_successor_index(sorted_rows, row_index)
            if successor_index is not None:
                yield _ClosedCase(
                    case_rows=(case_row,),
                    terminal_status="intermediate_continuation",
                )
                continue

            yield _ClosedCase(
                case_rows=tuple(current_case),
                terminal_status=HOW_ENDED_CONTINUATION,
            )
            current_case = []
            start_new_case = True
            continue

        if status in {
            HOW_ENDED_GOOD,
            HOW_ENDED_ENUCLEATION,
            HOW_ENDED_NO_FOLLOWUP,
        }:
            yield _ClosedCase(
                case_rows=tuple(current_case),
                terminal_status=status,
            )
            current_case = []
            start_new_case = True
            continue

        yield _ClosedCase(
            case_rows=tuple(current_case),
            terminal_status=None,
        )
        current_case = []
        start_new_case = True


def _case_record_from_closed_case(closed: _ClosedCase) -> TreatmentCaseRecord:
    case_rows = closed.case_rows
    terminal_row = case_rows[-1]
    start_date = case_rows[0].appointment_date
    end_date: date | None = None
    duration_days: int | None = None

    if closed.terminal_status == HOW_ENDED_GOOD:
        end_date = terminal_row.last_appointment_date
        if start_date is not None and end_date is not None and end_date >= start_date:
            duration_days = (end_date - start_date).days

    return TreatmentCaseRecord(
        patient_id=terminal_row.patient_id,
        eye=terminal_row.eye,
        terminal_status=closed.terminal_status,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        terminal_row_index=terminal_row.row_index,
        row_indices=tuple(row.row_index for row in case_rows),
        terminal_ulcer_code=terminal_row.ulcer_code,
    )


def _resolved_clinical_columns(
    clinical: pd.DataFrame,
) -> dict[str, str | None]:
    return {
        "patient_id": resolve_column(clinical, PATIENT_ID_COLUMN),
        "eye": resolve_column(clinical, "eye"),
        "appointment": resolve_column(clinical, "date_appointment_first_before_micro"),
        "how_ended": resolve_column(clinical, "how_ended"),
        "last_appointment": resolve_column(clinical, DATE_LAST_APPOINTMENT_COLUMN),
        "ulcer": resolve_column(clinical, "type_of_ulcer"),
    }


def _clinical_case_rows_from_frame(
    clinical: pd.DataFrame,
    *,
    columns: dict[str, str | None],
    row_filter: pd.Series | None = None,
) -> list[_ClinicalCaseRow]:
    patient_id_col = columns["patient_id"]
    if patient_id_col is None:
        return []

    frame = clinical if row_filter is None else clinical.loc[row_filter]
    case_rows: list[_ClinicalCaseRow] = []
    for row_index, row in frame.iterrows():
        patient_id = normalize_patient_id(row[patient_id_col])
        if patient_id is None:
            continue
        case_row = _clinical_case_row_from_series(
            row_index,
            row,
            patient_id=patient_id,
            eye_column=columns["eye"],
            appointment_column=columns["appointment"],
            how_ended_column=columns["how_ended"],
            last_appointment_column=columns["last_appointment"],
            ulcer_column=columns["ulcer"],
        )
        if case_row is not None:
            case_rows.append(case_row)
    return case_rows


def enumerate_treatment_cases(clinical: pd.DataFrame) -> tuple[TreatmentCaseRecord, ...]:
    columns = _resolved_clinical_columns(clinical)
    case_rows = _clinical_case_rows_from_frame(clinical, columns=columns)
    cases: list[TreatmentCaseRecord] = []

    grouped: dict[tuple[str, str], list[_ClinicalCaseRow]] = {}
    for case_row in case_rows:
        grouped.setdefault((case_row.patient_id, case_row.eye), []).append(case_row)

    for group_rows in grouped.values():
        sorted_rows = _sort_case_rows(group_rows)
        for closed in _iter_closed_cases(sorted_rows):
            if closed.terminal_status == "intermediate_continuation":
                continue
            cases.append(_case_record_from_closed_case(closed))

    return tuple(cases)


def filter_healed_cases_with_duration(
    clinical: pd.DataFrame,
) -> tuple[tuple[HealedCaseWithDuration, ...], TreatmentCaseExclusionSummary]:
    columns = _resolved_clinical_columns(clinical)
    ulcer_col = columns["ulcer"]
    total_rows = len(clinical)

    if ulcer_col is None:
        return (), TreatmentCaseExclusionSummary(
            total_clinical_rows=total_rows,
            excluded_non_ulcer=total_rows,
            excluded_not_good=0,
            excluded_enucleation=0,
            excluded_no_followup=0,
            excluded_continuation=0,
            excluded_duration_unavailable=0,
            included_healed_with_duration=0,
        )

    ulcer_mask = clinical[ulcer_col].map(normalize_ulcer_code).notna()
    excluded_non_ulcer = int((~ulcer_mask).sum())
    ulcer_frame = clinical.loc[ulcer_mask]
    cases = enumerate_treatment_cases(ulcer_frame)

    excluded_not_good = 0
    excluded_enucleation = 0
    excluded_no_followup = 0
    excluded_continuation = 0
    excluded_duration_unavailable = 0
    healed_cases: list[HealedCaseWithDuration] = []

    for case in cases:
        if case.terminal_status == HOW_ENDED_ENUCLEATION:
            excluded_enucleation += 1
            continue
        if case.terminal_status == HOW_ENDED_NO_FOLLOWUP:
            excluded_no_followup += 1
            continue
        if case.terminal_status == HOW_ENDED_CONTINUATION:
            excluded_continuation += 1
            continue
        if case.terminal_status != HOW_ENDED_GOOD:
            excluded_not_good += 1
            continue
        if case.duration_days is None:
            excluded_duration_unavailable += 1
            continue
        healed_cases.append(
            HealedCaseWithDuration(
                patient_id=case.patient_id,
                eye=case.eye,
                duration_days=case.duration_days,
                terminal_ulcer_code=case.terminal_ulcer_code,
                terminal_row_index=case.terminal_row_index,
            )
        )

    return tuple(healed_cases), TreatmentCaseExclusionSummary(
        total_clinical_rows=total_rows,
        excluded_non_ulcer=excluded_non_ulcer,
        excluded_not_good=excluded_not_good,
        excluded_enucleation=excluded_enucleation,
        excluded_no_followup=excluded_no_followup,
        excluded_continuation=excluded_continuation,
        excluded_duration_unavailable=excluded_duration_unavailable,
        included_healed_with_duration=len(healed_cases),
    )


def build_treatment_duration_by_row(
    matched: pd.DataFrame,
    clinical: pd.DataFrame,
) -> dict[Hashable, str]:
    columns = _resolved_clinical_columns(clinical)
    patient_id_col = columns["patient_id"]
    if patient_id_col is None or matched.empty:
        return {}

    case_rows: list[_ClinicalCaseRow] = []
    for row_index, row in matched.iterrows():
        patient_id = normalize_patient_id(row[patient_id_col])
        if patient_id is None:
            continue
        case_row = _clinical_case_row_from_series(
            row_index,
            row,
            patient_id=patient_id,
            eye_column=columns["eye"],
            appointment_column=columns["appointment"],
            how_ended_column=columns["how_ended"],
            last_appointment_column=columns["last_appointment"],
            ulcer_column=columns["ulcer"],
        )
        if case_row is not None:
            case_rows.append(case_row)

    case_rows_by_eye: dict[str, list[_ClinicalCaseRow]] = {}
    for case_row in case_rows:
        case_rows_by_eye.setdefault(case_row.eye, []).append(case_row)

    duration_by_row: dict[Hashable, str] = {}
    for eye_rows in case_rows_by_eye.values():
        sorted_rows = _sort_case_rows(eye_rows)
        current_case: list[_ClinicalCaseRow] = []
        start_new_case = True

        for row_index, case_row in enumerate(sorted_rows):
            if start_new_case:
                current_case = []
                start_new_case = False

            current_case.append(case_row)
            status = case_row.how_ended

            if status == HOW_ENDED_CONTINUATION:
                successor_index = _find_continuation_successor_index(
                    sorted_rows,
                    row_index,
                )
                if successor_index is not None:
                    duration_by_row[case_row.row_index] = TREATMENT_DURATION_CONTINUED
                    continue

                _close_duration_case(
                    duration_by_row,
                    current_case,
                    terminal_status=HOW_ENDED_CONTINUATION,
                )
                current_case = []
                start_new_case = True
                continue

            if status == HOW_ENDED_GOOD:
                _close_duration_case(
                    duration_by_row,
                    current_case,
                    terminal_status=HOW_ENDED_GOOD,
                )
                current_case = []
                start_new_case = True
                continue

            if status == HOW_ENDED_ENUCLEATION:
                _close_duration_case(
                    duration_by_row,
                    current_case,
                    terminal_status=HOW_ENDED_ENUCLEATION,
                )
                current_case = []
                start_new_case = True
                continue

            if status == HOW_ENDED_NO_FOLLOWUP:
                _close_duration_case(
                    duration_by_row,
                    current_case,
                    terminal_status=HOW_ENDED_NO_FOLLOWUP,
                )
                current_case = []
                start_new_case = True
                continue

            _close_duration_case(
                duration_by_row,
                current_case,
                terminal_status=None,
            )
            current_case = []
            start_new_case = True

    for row_index in matched.index:
        duration_by_row.setdefault(row_index, TREATMENT_DURATION_UNAVAILABLE)

    return duration_by_row
