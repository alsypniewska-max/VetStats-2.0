from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.resistance_over_time import (
    ExclusionSummary,
    ResistanceOverTimeResult,
    compute_resistance_over_time,
)


class ResistanceOverTimeService:
    def analyze(self) -> ResistanceOverTimeResult:
        micro_path = self._resolve_micro_path()
        if micro_path is None:
            return ResistanceOverTimeResult(
                source_label="micro",
                exclusions=ExclusionSummary(0, 0, 0, 0, 0),
                yearly_summaries=(),
                has_sensitivity_data=False,
                error_message="Nie znaleziono pliku micro.csv ani micro_sterile.csv.",
            )

        micro = load_csv(micro_path)
        return compute_resistance_over_time(
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
