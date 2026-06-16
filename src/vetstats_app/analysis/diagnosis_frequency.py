from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from vetstats_app.analysis.report_models import ReportTableBlock

TYPE_OF_ULCER_COLUMN = "type_of_ulcer"
UNKNOWN_VALUE = "xxx"

DIAGNOSIS_CODE_MAPPING: list[tuple[str, str]] = [
    ("s", "stromal"),
    ("e", "epithelial"),
    ("p", "perforative"),
    ("n", "neurotrophic"),
    ("m", "melting"),
    ("sceed", "SCEED"),
    ("x", "other"),
]

DIAGNOSIS_LABELS: dict[str, str] = dict(DIAGNOSIS_CODE_MAPPING)
VALID_CODES = frozenset(DIAGNOSIS_LABELS)


@dataclass(frozen=True)
class DiagnosisFrequencyRow:
    code: str
    label: str
    count: int
    percentage: float


@dataclass(frozen=True)
class DiagnosisFrequencyResult:
    total_cases: int
    included_cases: int
    excluded_cases: int
    frequencies: tuple[DiagnosisFrequencyRow, ...]
    source_label: str
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def _resolve_type_of_ulcer_column(clinical: pd.DataFrame) -> str | None:
    if TYPE_OF_ULCER_COLUMN in clinical.columns:
        return TYPE_OF_ULCER_COLUMN

    lower_to_actual = {
        str(column).strip().lower(): str(column).strip()
        for column in clinical.columns
    }
    return lower_to_actual.get(TYPE_OF_ULCER_COLUMN)


def normalize_ulcer_code(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    code = str(value).strip().lower()
    if not code or code == UNKNOWN_VALUE:
        return None
    if code in VALID_CODES:
        return code
    return None


def compute_diagnosis_frequency(
    clinical: pd.DataFrame,
    *,
    source_label: str = "clinical",
) -> DiagnosisFrequencyResult:
    column_name = _resolve_type_of_ulcer_column(clinical)
    if column_name is None:
        return DiagnosisFrequencyResult(
            total_cases=len(clinical),
            included_cases=0,
            excluded_cases=len(clinical),
            frequencies=(),
            source_label=source_label,
            error_message="Brak kolumny type_of_ulcer w tabeli clinical.",
        )

    total_cases = len(clinical)
    normalized_codes = clinical[column_name].map(normalize_ulcer_code)
    included_codes = normalized_codes.dropna()
    included_cases = len(included_codes)
    excluded_cases = total_cases - included_cases

    counts = included_codes.value_counts()
    frequencies: list[DiagnosisFrequencyRow] = []
    for code, label in DIAGNOSIS_CODE_MAPPING:
        count = int(counts.get(code, 0))
        percentage = (count / included_cases * 100.0) if included_cases else 0.0
        frequencies.append(
            DiagnosisFrequencyRow(
                code=code,
                label=label,
                count=count,
                percentage=percentage,
            )
        )

    return DiagnosisFrequencyResult(
        total_cases=total_cases,
        included_cases=included_cases,
        excluded_cases=excluded_cases,
        frequencies=tuple(frequencies),
        source_label=source_label,
    )


def build_interpretation_summary(result: DiagnosisFrequencyResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się obliczyć częstości rozpoznań."

    if result.included_cases == 0:
        return "Brak przypadków z prawidłowym kodem type_of_ulcer do analizy."

    observed = [row for row in result.frequencies if row.count > 0]
    if not observed:
        return "Brak przypadków z prawidłowym kodem type_of_ulcer do analizy."

    most_common = max(observed, key=lambda row: (row.count, row.label))
    least_common = min(observed, key=lambda row: (row.count, row.label))

    return (
        f"Przeanalizowano {result.included_cases} z {result.total_cases} przypadków "
        f"(wykluczono {result.excluded_cases} z brakującymi lub nieprawidłowymi kodami). "
        f"Najczęstsze rozpoznanie: {most_common.label} ({most_common.count}, "
        f"{most_common.percentage:.1f}%). "
        f"Najrzadsze rozpoznanie: {least_common.label} ({least_common.count}, "
        f"{least_common.percentage:.1f}%)."
    )


def build_descriptive_stats_block(
    result: DiagnosisFrequencyResult,
) -> ReportTableBlock:
    total_n = result.total_cases
    included_n = result.included_cases
    excluded_n = result.excluded_cases
    included_pct = (included_n / total_n * 100.0) if total_n else 0.0
    excluded_pct = (excluded_n / total_n * 100.0) if total_n else 0.0

    observed = [row for row in result.frequencies if row.count > 0]
    nonzero_categories = len(observed)

    if observed:
        most_common = max(observed, key=lambda row: (row.count, row.label))
        most_common_label = most_common.label
        most_common_count = str(most_common.count)
        most_common_percentage = f"{most_common.percentage:.1f}"
    else:
        most_common_label = "—"
        most_common_count = "0"
        most_common_percentage = "0.0"

    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba przypadków (N)", str(total_n)),
            ("Uwzględnione (n)", str(included_n)),
            ("Wykluczone (n)", str(excluded_n)),
            ("Uwzględnione (%)", f"{included_pct:.1f}"),
            ("Wykluczone (%)", f"{excluded_pct:.1f}"),
            ("Liczba kategorii z danymi", str(nonzero_categories)),
            ("Najczęstsza kategoria", most_common_label),
            ("Liczba — najczęstsza kategoria", most_common_count),
            ("Udział (%) — najczęstsza kategoria", most_common_percentage),
        ),
    )
