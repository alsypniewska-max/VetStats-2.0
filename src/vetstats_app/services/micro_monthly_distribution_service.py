from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.micro_monthly_distribution import (
    MicroMonthlyDistributionResult,
    build_monthly_distribution,
    compute_micro_monthly_distribution,
)


class MicroMonthlyDistributionService:
    def analyze(self) -> MicroMonthlyDistributionResult:
        micro_path = self._resolve_micro_path()
        if micro_path is None:
            return MicroMonthlyDistributionResult(
                source_label="micro",
                total_rows=0,
                excluded_invalid_date_collect=0,
                excluded_missing_result_id=0,
                included_swabs=0,
                observed_years=(),
                yearly_distributions=(),
                combined_distribution=build_monthly_distribution(()),
                error_message="Nie znaleziono pliku micro.csv ani micro_sterile.csv.",
            )

        micro = load_csv(micro_path)
        return compute_micro_monthly_distribution(
            micro,
            source_label=micro_path.name,
        )

    def _resolve_micro_path(self) -> Path | None:
        candidates = (
            DEFAULT_OUTPUT_DIR / sterile_output_name("micro.csv"),
            DEFAULT_INPUT_DIR / "micro.csv",
        )
        for path in candidates:
            if path.is_file():
                return path
        return None
