from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.diagnosis_frequency import (
    DiagnosisFrequencyResult,
    compute_diagnosis_frequency,
)


class DiagnosisFrequencyService:
    def analyze(self) -> DiagnosisFrequencyResult:
        clinical_path = self._resolve_clinical_path()
        if clinical_path is None:
            return DiagnosisFrequencyResult(
                total_cases=0,
                included_cases=0,
                excluded_cases=0,
                frequencies=(),
                source_label="clinical",
                error_message=(
                    "Nie znaleziono pliku clinical.csv ani clinical_sterile.csv."
                ),
            )

        clinical = load_csv(clinical_path)
        return compute_diagnosis_frequency(
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
