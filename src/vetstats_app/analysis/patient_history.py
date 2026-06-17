from __future__ import annotations

import re
from collections.abc import Callable
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
        formatter = PATIENT_FIELD_VALUE_FORMATTERS.get(field_name, format_display_value)
        patient_fields.append(
            PatientFieldRow(
                field_name=field_name,
                label=label,
                value=formatter(patient_row[column]),
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
