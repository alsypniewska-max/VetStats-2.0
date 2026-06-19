from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from data_sterilizer.schemas.clinical import (
    DRUG_BEFORE_MICRO_COLUMN,
    NOT_APPLICABLE_VALUE,
)
from data_sterilizer.schemas.micro import NEGATIVE_BACTERIA_VALUE
from vetstats_app.analysis.clinical_common import resolve_column
from vetstats_app.analysis.clinical_micro_matching import (
    ClinicalMicroMatchingSummary,
    match_clinical_rows_to_micro_bacteria,
    normalize_micro_bacteria,
)
from vetstats_app.analysis.report_models import ReportTableBlock

UNKNOWN_VALUE = "xxx"
NO_PRIOR_TREATMENT_VALUE = NOT_APPLICABLE_VALUE

NO_PRIOR_TREATMENT_LABEL = "Brak leczenia przed wymazem"
UNKNOWN_DRUG_LABEL = "Nieznany lek przed wymazem"
TREATED_BEFORE_SWAB_LABEL = "Leczenie przed wymazem"

CULTURE_OUTCOME_NEGATIVE = "Wynik negatywny"
CULTURE_OUTCOME_SINGLE = "Pojedynczy wzrost bakteryjny"
CULTURE_OUTCOME_MIXED = "Wzrost mieszany"
CULTURE_OUTCOME_UNKNOWN = "Nieznany wynik posiewu"

CULTURE_OUTCOME_ORDER: tuple[str, ...] = (
    CULTURE_OUTCOME_NEGATIVE,
    CULTURE_OUTCOME_SINGLE,
    CULTURE_OUTCOME_MIXED,
    CULTURE_OUTCOME_UNKNOWN,
)

TREATMENT_STATUS_ORDER: tuple[str, ...] = (
    TREATED_BEFORE_SWAB_LABEL,
    NO_PRIOR_TREATMENT_LABEL,
    UNKNOWN_DRUG_LABEL,
)

DrugFieldBucket = Literal["no_prior_treatment", "unknown", "drugs"]


def _polish_case_count(count: int, singular: str, plural: str) -> str:
    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural}"


@dataclass(frozen=True)
class DrugFrequencyRow:
    drug_label: str
    count: int
    percentage: float


@dataclass(frozen=True)
class CultureOutcomeRow:
    outcome_label: str
    count: int
    percentage: float


@dataclass(frozen=True)
class DrugCultureCrossTabRow:
    drug_label: str
    culture_outcome: str
    count: int


@dataclass(frozen=True)
class TreatmentStatusCultureCrossTabRow:
    treatment_status_label: str
    culture_outcome: str
    count: int


@dataclass(frozen=True)
class PreSwabDrugsResult:
    source_clinical_label: str
    source_micro_label: str
    matching: ClinicalMicroMatchingSummary
    total_clinical_rows: int
    no_prior_treatment_count: int
    unknown_drug_count: int
    with_known_drugs_count: int
    top_drugs: tuple[DrugFrequencyRow, ...]
    culture_outcomes: tuple[CultureOutcomeRow, ...]
    drug_culture_crosstab: tuple[DrugCultureCrossTabRow, ...]
    treatment_status_culture_crosstab: tuple[TreatmentStatusCultureCrossTabRow, ...]
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error_message is None


def normalize_drug_token(token: str) -> str | None:
    text = " ".join(token.strip().lower().split())
    if not text or text in {UNKNOWN_VALUE, NO_PRIOR_TREATMENT_VALUE}:
        return None
    return text


def split_drug_tokens_from_text(text: str) -> tuple[str, ...]:
    if ";" in text:
        raw_parts = text.split(";")
    else:
        raw_parts = [text]
    tokens: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        normalized = normalize_drug_token(part)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(normalized)
    return tuple(tokens)


def classify_drug_field(value: object) -> tuple[DrugFieldBucket, tuple[str, ...]]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "unknown", ()
    text = str(value).strip().lower()
    if not text:
        return "unknown", ()
    if text == UNKNOWN_VALUE:
        return "unknown", ()
    if text == NO_PRIOR_TREATMENT_VALUE:
        return "no_prior_treatment", ()
    tokens = split_drug_tokens_from_text(text)
    if not tokens:
        return "unknown", ()
    return "drugs", tokens


def classify_culture_outcome(bacteria_values: tuple[str, ...]) -> str:
    normalized = tuple(
        bacteria
        for bacteria in (normalize_micro_bacteria(value) for value in bacteria_values)
        if bacteria is not None
    )
    if not normalized:
        return CULTURE_OUTCOME_UNKNOWN

    non_negative = tuple(
        bacteria for bacteria in normalized if bacteria != NEGATIVE_BACTERIA_VALUE
    )
    if not non_negative:
        return CULTURE_OUTCOME_NEGATIVE

    unique_positive = set(non_negative)
    if len(unique_positive) == 1:
        return CULTURE_OUTCOME_SINGLE
    return CULTURE_OUTCOME_MIXED


def _drug_label_for_bucket(bucket: DrugFieldBucket) -> str | None:
    if bucket == "no_prior_treatment":
        return NO_PRIOR_TREATMENT_LABEL
    if bucket == "unknown":
        return UNKNOWN_DRUG_LABEL
    return None


def treatment_status_label_for_bucket(bucket: DrugFieldBucket) -> str:
    if bucket == "drugs":
        return TREATED_BEFORE_SWAB_LABEL
    if bucket == "no_prior_treatment":
        return NO_PRIOR_TREATMENT_LABEL
    return UNKNOWN_DRUG_LABEL


def _build_treatment_status_culture_crosstab(
    counter: Counter[tuple[str, str]],
) -> tuple[TreatmentStatusCultureCrossTabRow, ...]:
    rows: list[TreatmentStatusCultureCrossTabRow] = []
    for treatment_status in TREATMENT_STATUS_ORDER:
        for culture_outcome in CULTURE_OUTCOME_ORDER:
            count = counter.get((treatment_status, culture_outcome), 0)
            if count:
                rows.append(
                    TreatmentStatusCultureCrossTabRow(
                        treatment_status_label=treatment_status,
                        culture_outcome=culture_outcome,
                        count=count,
                    )
                )
    return tuple(rows)


def compute_pre_swab_drugs(
    clinical: pd.DataFrame,
    micro: pd.DataFrame,
    *,
    source_clinical_label: str = "clinical",
    source_micro_label: str = "micro",
    top_drug_limit: int = 15,
) -> PreSwabDrugsResult:
    drug_column = resolve_column(clinical, DRUG_BEFORE_MICRO_COLUMN)
    if drug_column is None:
        drug_column = resolve_column(clinical, "drugs_used_before_micro")
    if drug_column is None:
        return PreSwabDrugsResult(
            source_clinical_label=source_clinical_label,
            source_micro_label=source_micro_label,
            matching=ClinicalMicroMatchingSummary(0, 0, 0, 0),
            total_clinical_rows=len(clinical),
            no_prior_treatment_count=0,
            unknown_drug_count=0,
            with_known_drugs_count=0,
            top_drugs=(),
            culture_outcomes=(),
            drug_culture_crosstab=(),
            treatment_status_culture_crosstab=(),
            error_message=(
                "Brak kolumny drug_used_before_micro w tabeli clinical."
            ),
        )

    total_clinical_rows = len(clinical)
    no_prior_treatment_count = 0
    unknown_drug_count = 0
    with_known_drugs_count = 0
    drug_token_counter: Counter[str] = Counter()

    clinical_drug_by_index: dict[object, tuple[DrugFieldBucket, tuple[str, ...]]] = {}
    for row_index, value in clinical[drug_column].items():
        bucket, tokens = classify_drug_field(value)
        clinical_drug_by_index[row_index] = (bucket, tokens)
        if bucket == "no_prior_treatment":
            no_prior_treatment_count += 1
        elif bucket == "unknown":
            unknown_drug_count += 1
        else:
            with_known_drugs_count += 1
            drug_token_counter.update(tokens)

    matched_pairs, matching = match_clinical_rows_to_micro_bacteria(clinical, micro)
    if matched_pairs.empty:
        top_drugs = _build_top_drugs(drug_token_counter, top_drug_limit)
        return PreSwabDrugsResult(
            source_clinical_label=source_clinical_label,
            source_micro_label=source_micro_label,
            matching=matching,
            total_clinical_rows=total_clinical_rows,
            no_prior_treatment_count=no_prior_treatment_count,
            unknown_drug_count=unknown_drug_count,
            with_known_drugs_count=with_known_drugs_count,
            top_drugs=top_drugs,
            culture_outcomes=(),
            drug_culture_crosstab=(),
            treatment_status_culture_crosstab=(),
        )

    bacteria_by_clinical_index: dict[object, list[str]] = {}
    for _, row in matched_pairs.iterrows():
        bacteria_by_clinical_index.setdefault(row["clinical_index"], []).append(
            str(row["bacteria"])
        )

    culture_counter: Counter[str] = Counter()
    crosstab_counter: Counter[tuple[str, str]] = Counter()
    treatment_status_culture_counter: Counter[tuple[str, str]] = Counter()

    for clinical_index, bacteria_values in bacteria_by_clinical_index.items():
        culture_outcome = classify_culture_outcome(tuple(bacteria_values))
        culture_counter[culture_outcome] += 1

        bucket, tokens = clinical_drug_by_index.get(clinical_index, ("unknown", ()))
        treatment_status = treatment_status_label_for_bucket(bucket)
        treatment_status_culture_counter[(treatment_status, culture_outcome)] += 1

        if bucket == "drugs":
            for drug in tokens:
                crosstab_counter[(drug, culture_outcome)] += 1
        else:
            label = _drug_label_for_bucket(bucket)
            if label is not None:
                crosstab_counter[(label, culture_outcome)] += 1

    culture_total = sum(culture_counter.values())
    culture_outcomes = tuple(
        CultureOutcomeRow(
            outcome_label=outcome,
            count=count,
            percentage=(count / culture_total * 100.0) if culture_total else 0.0,
        )
        for outcome, count in sorted(
            culture_counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )

    drug_culture_crosstab = tuple(
        DrugCultureCrossTabRow(
            drug_label=drug_label,
            culture_outcome=culture_outcome,
            count=count,
        )
        for (drug_label, culture_outcome), count in sorted(
            crosstab_counter.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
    )

    return PreSwabDrugsResult(
        source_clinical_label=source_clinical_label,
        source_micro_label=source_micro_label,
        matching=matching,
        total_clinical_rows=total_clinical_rows,
        no_prior_treatment_count=no_prior_treatment_count,
        unknown_drug_count=unknown_drug_count,
        with_known_drugs_count=with_known_drugs_count,
        top_drugs=_build_top_drugs(drug_token_counter, top_drug_limit),
        culture_outcomes=culture_outcomes,
        drug_culture_crosstab=drug_culture_crosstab,
        treatment_status_culture_crosstab=_build_treatment_status_culture_crosstab(
            treatment_status_culture_counter
        ),
    )


def _build_top_drugs(
    drug_token_counter: Counter[str],
    top_drug_limit: int,
) -> tuple[DrugFrequencyRow, ...]:
    total_tokens = sum(drug_token_counter.values())
    rows: list[DrugFrequencyRow] = []
    for drug, count in drug_token_counter.most_common(top_drug_limit):
        rows.append(
            DrugFrequencyRow(
                drug_label=drug,
                count=count,
                percentage=(count / total_tokens * 100.0) if total_tokens else 0.0,
            )
        )
    return tuple(rows)


def build_summary_details(result: PreSwabDrugsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przeanalizować leków przed wymazem."

    matching = result.matching
    return (
        f"Źródła danych: {result.source_clinical_label}, {result.source_micro_label}. "
        f"Przeanalizowano {result.total_clinical_rows} wierszy clinical; dopasowano "
        f"{matching.matched_pairs} do wyników micro. "
        f"Brak leczenia przed wymazem (x): {result.no_prior_treatment_count}. "
        f"Nieznany wpis leku: {result.unknown_drug_count}."
    )


def build_interpretation_summary(result: PreSwabDrugsResult) -> str:
    if not result.is_success:
        return result.error_message or "Nie udało się przygotować interpretacji."

    if result.total_clinical_rows == 0:
        return "Brak danych clinical do analizy leków przed wymazem."

    parts: list[str] = [
        (
            f"W {result.total_clinical_rows} wierszach clinical pole "
            f"drug_used_before_micro wskazuje brak leczenia (x) w "
            f"{_polish_case_count(result.no_prior_treatment_count, 'przypadku', 'przypadkach')}, "
            f"nieznany wpis w "
            f"{_polish_case_count(result.unknown_drug_count, 'przypadku', 'przypadkach')}, "
            f"a konkretne leki w "
            f"{_polish_case_count(result.with_known_drugs_count, 'przypadku', 'przypadkach')}."
        )
    ]

    if result.top_drugs:
        top = result.top_drugs[0]
        if len(result.top_drugs) > 1:
            runner_up = result.top_drugs[1]
            parts.append(
                f"Najczęściej powtarzający się lek to {top.drug_label} "
                f"({top.count} wystąpień, {top.percentage:.1f}% wszystkich podań), "
                f"przed {runner_up.drug_label} ({runner_up.count})."
            )
        else:
            parts.append(
                f"Jedyny zidentyfikowany lek przed wymazem: {top.drug_label} "
                f"({top.count} wystąpień)."
            )
    else:
        parts.append(
            "W danych clinical nie zidentyfikowano nazw leków stosowanych przed wymazem."
        )

    if result.matching.matched_pairs == 0:
        parts.append(
            "Brak dopasowanych par clinical–micro, więc wykresy wyników posiewu "
            "nie mają podstawy w danych."
        )
        return " ".join(parts)

    parts.append(
        f"Dopasowanie clinical–micro objęło "
        f"{_polish_case_count(result.matching.matched_pairs, 'przypadek', 'przypadki')} "
        f"nadających się do oceny wyniku posiewu."
    )

    if result.culture_outcomes:
        dominant = result.culture_outcomes[0]
        parts.append(
            f"Po dopasowaniu najczęściej obserwuje się "
            f"{dominant.outcome_label.lower()} ({dominant.count}, "
            f"{dominant.percentage:.1f}% przypadków)."
        )
        if len(result.culture_outcomes) > 1:
            runner_up = result.culture_outcomes[1]
            parts.append(
                f"Kolejna kategoria to {runner_up.outcome_label.lower()} "
                f"({_polish_case_count(runner_up.count, 'przypadek', 'przypadki')})."
            )

    if result.top_drugs and result.drug_culture_crosstab:
        top_drug = result.top_drugs[0].drug_label
        top_drug_rows = [
            row
            for row in result.drug_culture_crosstab
            if row.drug_label == top_drug
        ]
        if top_drug_rows:
            leading = max(top_drug_rows, key=lambda row: (row.count, row.culture_outcome))
            parts.append(
                f"Przy leku {top_drug} dominuje {leading.culture_outcome.lower()} "
                f"({_polish_case_count(leading.count, 'dopasowany przypadek', 'dopasowane przypadki')})."
            )

    no_prior_rows = [
        row
        for row in result.drug_culture_crosstab
        if row.drug_label == NO_PRIOR_TREATMENT_LABEL
    ]
    if no_prior_rows:
        leading = max(no_prior_rows, key=lambda row: (row.count, row.culture_outcome))
        parts.append(
            f"Gdy przed wymazem nie stosowano leczenia (x), najczęściej występuje "
            f"{leading.culture_outcome.lower()} "
            f"({_polish_case_count(leading.count, 'przypadek', 'przypadki')})."
        )

    if result.treatment_status_culture_crosstab:
        status_totals: Counter[str] = Counter()
        for row in result.treatment_status_culture_crosstab:
            status_totals[row.treatment_status_label] += row.count

        status_highlights: list[str] = []
        for treatment_status in TREATMENT_STATUS_ORDER:
            if treatment_status not in status_totals:
                continue
            status_rows = [
                row
                for row in result.treatment_status_culture_crosstab
                if row.treatment_status_label == treatment_status
            ]
            leading = max(status_rows, key=lambda row: (row.count, row.culture_outcome))
            status_highlights.append(
                f"{treatment_status.lower()}: {leading.culture_outcome.lower()} "
                f"({leading.count} z {status_totals[treatment_status]})"
            )

        if status_highlights:
            parts.append(
                "Porównanie statusu leczenia z wynikiem posiewu wskazuje — "
                + "; ".join(status_highlights)
                + "."
            )

    return " ".join(parts)


def build_descriptive_stats_block(result: PreSwabDrugsResult) -> ReportTableBlock:
    matching = result.matching
    return ReportTableBlock(
        title="Statystyki opisowe",
        columns=("Metryka", "Wartość"),
        rows=(
            ("Łączna liczba wierszy clinical (N)", str(result.total_clinical_rows)),
            ("Brak leczenia przed wymazem — x (n)", str(result.no_prior_treatment_count)),
            ("Nieznany / nieużyteczny wpis leku (n)", str(result.unknown_drug_count)),
            ("Wiersze z podanymi lekami (n)", str(result.with_known_drugs_count)),
            ("Dopasowane pary clinical–micro (n)", str(matching.matched_pairs)),
            ("Niedopasowane wiersze clinical (n)", str(matching.unmatched_clinical_rows)),
            (
                "Pacjenci z wieloma result_ID (n)",
                str(matching.patients_with_multiple_results),
            ),
            ("Unikalne leki w analizie (n)", str(len(result.top_drugs))),
            ("Kategorie wyniku posiewu (n)", str(len(result.culture_outcomes))),
        ),
    )


def top_drugs_table_block(result: PreSwabDrugsResult) -> ReportTableBlock:
    return ReportTableBlock(
        title="Najczęściej stosowane leki przed wymazem",
        columns=("Lek", "Liczba", "Udział (%)"),
        rows=tuple(
            (row.drug_label, str(row.count), f"{row.percentage:.1f}")
            for row in result.top_drugs
        ),
    )


def culture_outcomes_table_block(result: PreSwabDrugsResult) -> ReportTableBlock:
    return ReportTableBlock(
        title="Wyniki posiewu w dopasowanych przypadkach",
        columns=("Wynik posiewu", "Liczba", "Udział (%)"),
        rows=tuple(
            (row.outcome_label, str(row.count), f"{row.percentage:.1f}")
            for row in result.culture_outcomes
        ),
    )


def drug_culture_crosstab_table_block(result: PreSwabDrugsResult) -> ReportTableBlock:
    return ReportTableBlock(
        title="Leki przed wymazem a wynik posiewu",
        columns=("Lek przed wymazem", "Wynik posiewu", "Liczba"),
        rows=tuple(
            (row.drug_label, row.culture_outcome, str(row.count))
            for row in result.drug_culture_crosstab
        ),
    )


def treatment_status_culture_crosstab_table_block(
    result: PreSwabDrugsResult,
) -> ReportTableBlock:
    return ReportTableBlock(
        title="Status leczenia przed wymazem a wynik posiewu",
        columns=("Status leczenia przed wymazem", "Wynik posiewu", "Liczba"),
        rows=tuple(
            (
                row.treatment_status_label,
                row.culture_outcome,
                str(row.count),
            )
            for row in result.treatment_status_culture_crosstab
        ),
    )
