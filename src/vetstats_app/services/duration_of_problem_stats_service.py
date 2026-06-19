from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.duration_of_problem_stats import (
    DurationOfProblemStatsResult,
    compute_duration_of_problem_stats,
)


class DurationOfProblemStatsService:
    def analyze(self) -> DurationOfProblemStatsResult:
        clinical_path = self._resolve_clinical_path()
        if clinical_path is None:
            return DurationOfProblemStatsResult(
                source_label="clinical",
                total_rows=0,
                excluded_non_ulcer=0,
                excluded_invalid_duration=0,
                included_rows=0,
                overall_mean_days=None,
                overall_median_days=None,
                overall_percentile_25_days=None,
                overall_percentile_75_days=None,
                by_ulcer_type=(),
                all_duration_days=(),
                duration_value_groups=(),
                shortest_ulcer_label=None,
                longest_ulcer_label=None,
                error_message=(
                    "Nie znaleziono pliku clinical.csv ani clinical_sterile.csv."
                ),
            )

        clinical = load_csv(clinical_path)
        return compute_duration_of_problem_stats(
            clinical,
            source_label=clinical_path.name,
        )

    def _resolve_clinical_path(self) -> Path | None:
        candidates = (
            DEFAULT_OUTPUT_DIR / sterile_output_name("clinical.csv"),
            DEFAULT_INPUT_DIR / "clinical.csv",
        )
        for path in candidates:
            if path.is_file():
                return path
        return None
