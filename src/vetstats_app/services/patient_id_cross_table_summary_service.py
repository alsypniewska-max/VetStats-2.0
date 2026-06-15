from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
import pandas as pd
from vetstats_app.analysis.patient_id_cross_table_summary import (
    PatientIdCrossTableSummaryResult,
    compute_patient_id_cross_table_summary,
)


class PatientIdCrossTableSummaryService:
    def analyze(self) -> PatientIdCrossTableSummaryResult:
        datasets: dict[str, pd.DataFrame] = {}
        source_labels: dict[str, str] = {}
        missing: list[str] = []

        for table_name in ("patient", "clinical", "micro"):
            path = self._resolve_dataset_path(f"{table_name}.csv")
            if path is None:
                missing.append(table_name)
                continue
            datasets[table_name] = load_csv(path)
            source_labels[table_name] = path.name

        if missing:
            return PatientIdCrossTableSummaryResult(
                tables=(),
                pairwise=(),
                in_all_three=0,
                only_in_single_table=(),
                error_message=(
                    "Nie znaleziono plików: " + ", ".join(missing) + "."
                ),
            )

        return compute_patient_id_cross_table_summary(
            datasets,
            source_labels=source_labels,
        )

    def _resolve_dataset_path(self, dataset_name: str) -> Path | None:
        candidates = (
            DEFAULT_OUTPUT_DIR / sterile_output_name(dataset_name),
            DEFAULT_INPUT_DIR / dataset_name,
        )
        for path in candidates:
            if path.is_file():
                return path
        return None
