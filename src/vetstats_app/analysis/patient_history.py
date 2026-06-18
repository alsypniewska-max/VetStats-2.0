from __future__ import annotations

import calendar
import re
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import date

import pandas as pd

from data_sterilizer.schemas.patient import (
    DATE_OF_BIRTH_COLUMN,
    DISEASES_NOT_OPHT_COLUMN,
    GENDER_COLUMN,
    OTHER_DISEASES_OPHT_COLUMN,
    PATIENT_ID_COLUMN,
)
from vetstats_app.analysis.diagnosis_frequency import DIAGNOSIS_LABELS
from vetstats_app.analysis.procedure_diagnosis_relationship import (
    PROCEDURE_DISPLAY_LABELS,
)
from vetstats_app.analysis.report_models import AnalysisSectionReport, ReportTableBlock
from vetstats_app.analysis.treatment_groups import (
    FARMACOLOGY_SURGERY_MAPPING,
    TOPICAL_SYSTEMIC_MAPPING,
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
    (DISEASES_NOT_OPHT_COLUMN, "Inne problemy nie okulistyczne"),
    (OTHER_DISEASES_OPHT_COLUMN, "Inne problemy okulistyczne"),
)

GENDER_DISPLAY_MAP: dict[str, str] = {"m": "samiec", "f": "samica"}

DISEASES_NOT_OPHT_NAME_MAP: dict[str, str] = {
    "x": "brak",
    "xxx": "nie wiadomo",
    "otitis": "zapalenie ucha",
    "alergy": "alergia",
    "alergy skin": "alergia skórna",
    "reflux": "refluks",
    "heart": "problemy z sercem",
    "pancreatitis": "zapalenie trzustki",
    "hypothyroidism": "niedoczynność tarczycy",
    "gastric": "problemy żołądkowo-jelitowe",
    "diabetes": "cukrzyca",
    "atrial complex": "zespół przedsionkowy",
    "skin problems": "problemy dermatologiczne",
    "facial nerve paralysis l": "porażenie nerwów twarzowych L",
    "facial nerve paralysis r": "porażenie nerwów twarzowych P",
    "facial nerve paralysis b": "porażenie nerwów twarzowych obustronne",
}

OPHTHALMIC_SIDE_LR: dict[str, str] = {"l": "L", "r": "P"}


@dataclass(frozen=True)
class _OphthalmicDiseaseSpec:
    base: str
    both_word: str
    location_map: dict[str, str] | None = None


OPHTHALMIC_DISEASE_SPECS: dict[str, _OphthalmicDiseaseSpec] = {
    "cataract": _OphthalmicDiseaseSpec("zaćma", "obustronna"),
    "kcs": _OphthalmicDiseaseSpec("KCS", "obustronne"),
    "conjunctivitis": _OphthalmicDiseaseSpec("zapalenie spojówek", "obustronne"),
    "bollous keratopathy": _OphthalmicDiseaseSpec(
        "keratopatia pęcherzowa", "obustronna"
    ),
    "sequestrum": _OphthalmicDiseaseSpec("martwak", "obustronnie"),
    "calcium dystrophy": _OphthalmicDiseaseSpec(
        "dystrofia wapniowa rogówki", "obustronna"
    ),
    "trichiasis": _OphthalmicDiseaseSpec(
        "trichiasis",
        "obustronne",
        {
            "lower": "powiek dolnych",
            "upper": "powiek górnych",
            "both": "powiek górnych i dolnych",
        },
    ),
    "distichiasis": _OphthalmicDiseaseSpec(
        "dwurzędowość rzęs",
        "obustronna",
        {
            "lower": "powiek dolnych",
            "upper": "powiek górnych",
            "both": "powiek górnych i dolnych",
        },
    ),
    "entropium": _OphthalmicDiseaseSpec(
        "entropium powiek",
        "obustronne",
        {"lower": "dolnych", "upper": "górnych", "both": "górnych i dolnych"},
    ),
    "ectropium": _OphthalmicDiseaseSpec(
        "ectropium powiek",
        "obustronne",
        {"lower": "dolnych", "upper": "górnych", "both": "górnych i dolnych"},
    ),
}

# Longest keys first so multi-word names match before any shorter prefix.
_OPHTHALMIC_DISEASE_KEYS: tuple[str, ...] = tuple(
    sorted(OPHTHALMIC_DISEASE_SPECS, key=len, reverse=True)
)


def _format_first_name(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL or not text:
        return text
    return text[:1].upper() + text[1:]


def _format_gender(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return text
    return GENDER_DISPLAY_MAP.get(text.lower(), text)


def _format_semicolon_name_list(value: object, name_map: dict[str, str]) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return text
    parts = [part.strip() for part in text.split(";")]
    resolved = [name_map.get(part, part) for part in parts if part]
    if not resolved:
        return UNKNOWN_LABEL
    return ", ".join(resolved)


def _resolve_no_eye(lowered: str) -> str | None:
    match = re.fullmatch(r"no\s+([lrb])\s+eyes?", lowered)
    if match is None:
        return None
    side = match.group(1)
    if side == "b":
        return "brak obu oczu"
    if side == "l":
        return "brak lewego oka"
    return "brak prawego oka"


def _parse_ophthalmic_location(words: list[str]) -> str | None:
    if words == ["lower"]:
        return "lower"
    if words == ["upper"]:
        return "upper"
    if sorted(words) == ["lower", "upper"]:
        return "both"
    return None


def _build_ophthalmic_value(
    spec: _OphthalmicDiseaseSpec,
    remainder: str,
) -> str | None:
    words = remainder.split()

    side: str | None = None
    if words and words[-1] in ("l", "r", "b"):
        side = words[-1]
        words = words[:-1]

    location: str | None = None
    if words:
        if spec.location_map is None:
            return None
        location = _parse_ophthalmic_location(words)
        if location is None:
            return None

    parts = [spec.base]
    if location is not None and spec.location_map is not None:
        parts.append(spec.location_map[location])
    if side is not None:
        parts.append(spec.both_word if side == "b" else OPHTHALMIC_SIDE_LR[side])
    return " ".join(parts)


def _resolve_ophthalmic_token(token: str) -> str:
    lowered = token.lower()
    if lowered == "x":
        return "brak"
    if lowered == UNKNOWN_VALUE:
        return UNKNOWN_LABEL

    no_eye = _resolve_no_eye(lowered)
    if no_eye is not None:
        return no_eye

    for key in _OPHTHALMIC_DISEASE_KEYS:
        if lowered == key or lowered.startswith(key + " "):
            resolved = _build_ophthalmic_value(
                OPHTHALMIC_DISEASE_SPECS[key],
                lowered[len(key):].strip(),
            )
            if resolved is not None:
                return resolved
            break

    return token


def _format_ophthalmic_disease_list(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return text
    parts = [part.strip() for part in text.split(";")]
    resolved = [_resolve_ophthalmic_token(part) for part in parts if part]
    if not resolved:
        return UNKNOWN_LABEL
    return ", ".join(resolved)


PATIENT_FIELD_VALUE_FORMATTERS: dict[str, Callable[[object], str]] = {
    "name": _format_first_name,
    GENDER_COLUMN: _format_gender,
    DISEASES_NOT_OPHT_COLUMN: lambda value: _format_semicolon_name_list(
        value, DISEASES_NOT_OPHT_NAME_MAP
    ),
    OTHER_DISEASES_OPHT_COLUMN: _format_ophthalmic_disease_list,
}

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

CLINICAL_DISPLAY_COLUMNS: tuple[str, ...] = (
    "eye",
    "type_of_ulcer",
    "date_appointment_first_before_micro",
    DATE_LAST_APPOINTMENT_COLUMN,
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

EYE_DISPLAY_MAP: dict[str, str] = {
    "l": "lewe",
    "r": "prawe",
    "b": "oba oczy",
}

HOW_ENDED_DISPLAY_MAP: dict[str, str] = {
    "good": "wyleczono",
    "continuation": "brak poprawy, kontynuowano leczenie",
    "enucleation": "usunięto oko",
    "no followup": "brak dalszej obserwacji",
}

GROWTH_DISPLAY_MAP: dict[str, str] = {
    "heavy": "liczny wzrost",
    "scant": "nieliczny wzrost",
}

DURATION_UNIT_MAP: dict[str, str] = {
    "day": "dni",
    "days": "dni",
    "week": "tygodnie",
    "weeks": "tygodnie",
    "month": "miesiące",
    "months": "miesiące",
    "monts": "miesiące",
    "year": "lata",
    "years": "lata",
}

_FARMACOLOGY_SURGERY_LABELS: dict[str, str] = dict(FARMACOLOGY_SURGERY_MAPPING)
_TOPICAL_SYSTEMIC_LABELS: dict[str, str] = dict(TOPICAL_SYSTEMIC_MAPPING)
NEGATIVE_MICRO_RESULT = "negative"
NOT_APPLICABLE_CODE = "x"


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
    age_text: str = UNKNOWN_LABEL
    clinical_summary_lines: tuple[str, ...] = ()
    micro_summary_lines: tuple[str, ...] = ()


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


def _polish_plural(count: int, one: str, few: str, many: str) -> str:
    count = abs(count)
    if count == 1:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def _parse_dmy_date(value: object) -> date | None:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return None
    parts = text.split(".")
    if len(parts) != 3:
        return None
    try:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_how_ended_code(value: object) -> str | None:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return None
    return text.lower()


def _normalize_eye_code(value: object) -> str | None:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return None
    return text.lower()


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


def _format_treatment_duration_text(
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


@dataclass(frozen=True)
class _ClinicalCaseRow:
    row_index: Hashable
    eye: str
    appointment_date: date | None
    how_ended: str | None
    last_appointment_date: date | None


def _clinical_case_row_from_series(
    row_index: Hashable,
    row: pd.Series,
    *,
    eye_column: str | None,
    appointment_column: str | None,
    how_ended_column: str | None,
    last_appointment_column: str | None,
) -> _ClinicalCaseRow | None:
    if eye_column is None:
        return None
    eye = _normalize_eye_code(row[eye_column])
    if eye is None:
        return None

    appointment_date = (
        _parse_dmy_date(row[appointment_column])
        if appointment_column is not None
        else None
    )
    how_ended = (
        _normalize_how_ended_code(row[how_ended_column])
        if how_ended_column is not None
        else None
    )
    last_appointment_date = (
        _parse_dmy_date(row[last_appointment_column])
        if last_appointment_column is not None
        else None
    )
    return _ClinicalCaseRow(
        row_index=row_index,
        eye=eye,
        appointment_date=appointment_date,
        how_ended=how_ended,
        last_appointment_date=last_appointment_date,
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


def _mark_intermediate_continuation_rows(
    duration_by_row: dict[Hashable, str],
    case_rows: list[_ClinicalCaseRow],
) -> None:
    for case_row in case_rows[:-1]:
        if case_row.how_ended == HOW_ENDED_CONTINUATION:
            duration_by_row[case_row.row_index] = TREATMENT_DURATION_CONTINUED


def _close_duration_case(
    duration_by_row: dict[Hashable, str],
    case_rows: list[_ClinicalCaseRow],
    *,
    terminal_status: str | None,
) -> None:
    if not case_rows:
        return
    _mark_intermediate_continuation_rows(duration_by_row, case_rows)
    terminal_row = case_rows[-1]
    end_date: date | None = None
    if terminal_status in {HOW_ENDED_GOOD, HOW_ENDED_ENUCLEATION}:
        end_date = terminal_row.last_appointment_date
    duration_by_row[terminal_row.row_index] = _format_treatment_duration_text(
        terminal_status=terminal_status,
        is_intermediate_continuation=False,
        start_date=case_rows[0].appointment_date,
        end_date=end_date,
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


def _build_treatment_duration_by_row(
    matched: pd.DataFrame,
    clinical: pd.DataFrame,
) -> dict[Hashable, str]:
    eye_column = _resolve_column(clinical, "eye")
    appointment_column = _resolve_column(
        clinical,
        "date_appointment_first_before_micro",
    )
    how_ended_column = _resolve_column(clinical, "how_ended")
    last_appointment_column = _resolve_column(
        clinical,
        DATE_LAST_APPOINTMENT_COLUMN,
    )

    case_rows_by_eye: dict[str, list[_ClinicalCaseRow]] = {}
    for row_index, row in matched.iterrows():
        case_row = _clinical_case_row_from_series(
            row_index,
            row,
            eye_column=eye_column,
            appointment_column=appointment_column,
            how_ended_column=how_ended_column,
            last_appointment_column=last_appointment_column,
        )
        if case_row is None:
            continue
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


def _append_treatment_duration_column(
    matched: pd.DataFrame,
    clinical_columns: tuple[str, ...],
    clinical_rows: tuple[tuple[str, ...], ...],
    duration_by_row: dict[Hashable, str],
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    if not clinical_rows:
        return clinical_columns, clinical_rows

    augmented_rows: list[tuple[str, ...]] = []
    for row_index, row_values in zip(matched.index, clinical_rows, strict=True):
        duration_text = duration_by_row.get(
            row_index,
            TREATMENT_DURATION_UNAVAILABLE,
        )
        augmented_rows.append(row_values + (duration_text,))

    return (
        clinical_columns + (TREATMENT_DURATION_DISPLAY_COLUMN,),
        tuple(augmented_rows),
    )


def _compute_age_text(value: object, *, today: date | None = None) -> str:
    born = _parse_dmy_date(value)
    if born is None:
        return UNKNOWN_LABEL
    today = today or date.today()
    if born > today:
        return UNKNOWN_LABEL

    years = today.year - born.year
    months = today.month - born.month
    if today.day < born.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12

    years_text = f"{years} {_polish_plural(years, 'rok', 'lata', 'lat')}"
    months_text = f"{months} {_polish_plural(months, 'miesiąc', 'miesiące', 'miesięcy')}"
    return f"{years_text}, {months_text}"


def _eye_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    return EYE_DISPLAY_MAP.get(text.lower(), text)


def _how_ended_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    return HOW_ENDED_DISPLAY_MAP.get(text.lower(), text)


def _ulcer_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    code = text.lower()
    if code == NOT_APPLICABLE_CODE:
        return "brak wrzodu / inny problem"
    return DIAGNOSIS_LABELS.get(code, text)


def _duration_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    normalized = text.replace(",", ".")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s+([a-zA-Z]+)\s*", normalized)
    if match is None:
        return text
    number, unit = match.group(1), match.group(2).lower()
    unit_pl = DURATION_UNIT_MAP.get(unit)
    if unit_pl is None:
        return text
    if number.endswith(".0"):
        number = number[:-2]
    return f"{number} {unit_pl}"


def _farmacology_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    return _FARMACOLOGY_SURGERY_LABELS.get(text.lower(), text)


def _topical_systemic_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    code = text.lower()
    if code == NOT_APPLICABLE_CODE:
        return "brak danych"
    return _TOPICAL_SYSTEMIC_LABELS.get(code, text)


def _surgery_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    if text.lower() == NOT_APPLICABLE_CODE:
        return "brak zabiegu"
    parts = [part.strip() for part in text.split(";") if part.strip()]
    resolved = [PROCEDURE_DISPLAY_LABELS.get(part.lower(), part) for part in parts]
    return ", ".join(resolved) if resolved else UNKNOWN_LABEL


def _growth_text(value: object) -> str:
    text = format_display_value(value)
    if text == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    code = text.lower()
    if code == NOT_APPLICABLE_CODE:
        return "nie określono"
    return GROWTH_DISPLAY_MAP.get(code, text)


def _matched_patient_rows(
    frame: pd.DataFrame,
    normalized_id: str,
) -> pd.DataFrame | None:
    patient_id_col = _resolve_column(frame, "patient_ID")
    if patient_id_col is None:
        return None
    return frame[
        frame[patient_id_col].map(
            lambda value: _matches_normalized_patient_id(value, normalized_id)
        )
    ]


def _build_clinical_summary_lines(
    clinical: pd.DataFrame,
    normalized_id: str,
    *,
    duration_by_row: dict[Hashable, str] | None = None,
) -> tuple[str, ...]:
    matched = _matched_patient_rows(clinical, normalized_id)
    if matched is None or matched.empty:
        return ("Brak powiązanych wierszy clinical dla tego pacjenta.",)

    if duration_by_row is None:
        duration_by_row = _build_treatment_duration_by_row(matched, clinical)

    resolved = {name: _resolve_column(clinical, name) for name in CLINICAL_DISPLAY_COLUMNS}
    lines = [f"Liczba wierszy clinical: {len(matched)}."]
    for index, (row_index, row) in enumerate(matched.iterrows(), start=1):
        def value_of(name: str) -> object:
            actual = resolved.get(name)
            return row[actual] if actual is not None else None

        eye = _eye_text(value_of("eye"))
        ulcer = _ulcer_text(value_of("type_of_ulcer"))
        first_visit = format_display_value(
            value_of("date_appointment_first_before_micro")
        )
        treatment_duration = duration_by_row.get(
            row_index,
            TREATMENT_DURATION_UNAVAILABLE,
        )
        duration = _duration_text(value_of("duration_of_problem"))
        farmacology = _farmacology_text(value_of("farmacology_surgery"))
        topical = _topical_systemic_text(value_of("topical_systemic"))
        surgery = _surgery_text(value_of("type_of_surgery"))
        how_ended = _how_ended_text(value_of("how_ended"))
        lines.append(
            f"Wizyta {index}: oko {eye}; rozpoznanie: {ulcer}; "
            f"pierwsza wizyta: {first_visit}; czas leczenia: {treatment_duration}; "
            f"czas trwania problemu przed wizytą okulistyczną: {duration}; "
            f"leczenie: {farmacology}, {topical}; zabieg: {surgery}; "
            f"zakończenie: {how_ended}."
        )
    return tuple(lines)


def _build_micro_summary_lines(
    micro: pd.DataFrame,
    normalized_id: str,
) -> tuple[str, ...]:
    matched = _matched_patient_rows(micro, normalized_id)
    if matched is None or matched.empty:
        return ("Brak powiązanych wymazów micro dla tego pacjenta.",)

    resolved = {name: _resolve_column(micro, name) for name in MICRO_DISPLAY_COLUMNS}

    def value_of(row: pd.Series, name: str) -> object:
        actual = resolved.get(name)
        return row[actual] if actual is not None else None

    grouped: dict[str, list[pd.Series]] = {}
    order: list[str] = []
    for _, row in matched.iterrows():
        result_id = format_display_value(value_of(row, "result_ID"))
        if result_id not in grouped:
            grouped[result_id] = []
            order.append(result_id)
        grouped[result_id].append(row)

    lines = [f"Liczba wymazów (result_ID): {len(order)}."]
    for result_id in order:
        rows = grouped[result_id]
        first = rows[0]
        collected = format_display_value(value_of(first, "date_collect"))
        resulted = format_display_value(value_of(first, "date_result"))

        organisms: list[str] = []
        for row in rows:
            bacteria = format_display_value(value_of(row, "bacteria"))
            if bacteria != UNKNOWN_LABEL and bacteria.lower() == NEGATIVE_MICRO_RESULT:
                organisms.append("nie zaobserwowano wzrostu bakterii")
            else:
                organisms.append(f"{bacteria} — {_growth_text(value_of(row, 'growth'))}")

        if len(organisms) == 1:
            organism_text = organisms[0]
        else:
            count_word = _polish_plural(
                len(organisms), "drobnoustrój", "drobnoustroje", "drobnoustrojów"
            )
            organism_text = f"{len(organisms)} {count_word}: " + "; ".join(organisms)

        lines.append(
            f"Wymaz {result_id}: pobranie {collected}, wynik {resulted}: {organism_text}."
        )
    return tuple(lines)


def build_patient_history_section_report(
    detail: PatientHistoryDetail,
    *,
    source_labels: tuple[str, ...] = (),
) -> AnalysisSectionReport:
    table_blocks: list[ReportTableBlock] = [
        ReportTableBlock(
            title="Dane pacjenta",
            columns=("Pole", "Wartość"),
            rows=tuple((field.label, field.value) for field in detail.patient_fields),
        )
    ]
    if detail.clinical_columns:
        table_blocks.append(
            ReportTableBlock(
                title="Powiązane wiersze clinical",
                columns=detail.clinical_columns,
                rows=detail.clinical_rows,
            )
        )
    if detail.micro_columns:
        table_blocks.append(
            ReportTableBlock(
                title="Powiązane wiersze micro",
                columns=detail.micro_columns,
                rows=detail.micro_rows,
            )
        )

    summary_details = "Podsumowanie clinical. " + " ".join(
        detail.clinical_summary_lines
    )
    interpretation_summary = "Podsumowanie micro. " + " ".join(
        detail.micro_summary_lines
    )

    return AnalysisSectionReport(
        section_title=f"Historia pacjenta {detail.patient_id}",
        source_labels=tuple(source_labels),
        summary_details=summary_details,
        interpretation_summary=interpretation_summary,
        table_blocks=tuple(table_blocks),
    )


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
        formatter = PATIENT_FIELD_VALUE_FORMATTERS.get(field_name, format_display_value)
        patient_fields.append(
            PatientFieldRow(
                field_name=field_name,
                label=label,
                value=formatter(patient_row[column]),
            )
        )

    dob_column = _resolve_column(patient, DATE_OF_BIRTH_COLUMN)
    age_text = (
        _compute_age_text(patient_row[dob_column])
        if dob_column is not None
        else UNKNOWN_LABEL
    )
    age_field = PatientFieldRow(
        field_name="patient_age",
        label="Wiek pacjenta",
        value=age_text,
    )
    insert_index = len(patient_fields)
    for position, field in enumerate(patient_fields):
        if field.field_name == DATE_OF_BIRTH_COLUMN:
            insert_index = position + 1
            break
    patient_fields.insert(insert_index, age_field)

    matched_clinical = _matched_patient_rows(clinical, normalized_id)
    duration_by_row: dict[Hashable, str] = {}
    if matched_clinical is not None and not matched_clinical.empty:
        duration_by_row = _build_treatment_duration_by_row(
            matched_clinical,
            clinical,
        )

    clinical_columns, clinical_rows = _rows_for_table(
        clinical,
        patient_id=normalized_id,
        columns=CLINICAL_DISPLAY_COLUMNS,
    )
    if matched_clinical is not None and not matched_clinical.empty:
        clinical_columns, clinical_rows = _append_treatment_duration_column(
            matched_clinical,
            clinical_columns,
            clinical_rows,
            duration_by_row,
        )
    micro_columns, micro_rows = _rows_for_table(
        micro,
        patient_id=normalized_id,
        columns=MICRO_DISPLAY_COLUMNS,
    )

    clinical_summary_lines = _build_clinical_summary_lines(
        clinical,
        normalized_id,
        duration_by_row=duration_by_row,
    )
    micro_summary_lines = _build_micro_summary_lines(micro, normalized_id)

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
        age_text=age_text,
        clinical_summary_lines=clinical_summary_lines,
        micro_summary_lines=micro_summary_lines,
    )
