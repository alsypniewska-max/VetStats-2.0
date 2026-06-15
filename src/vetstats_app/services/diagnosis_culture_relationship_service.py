from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.diagnosis_culture_relationship import (
    DiagnosisCultureRelationshipResult,
    MatchingSummary,
    compute_diagnosis_culture_relationship,
)


class DiagnosisCultureRelationshipService:
    def analyze(self) -> DiagnosisCultureRelationshipResult:
        clinical_path = self._resolve_dataset_path("clinical.csv")
        micro_path = self._resolve_dataset_path("micro.csv")

        if clinical_path is None or micro_path is None:
            missing = []
            if clinical_path is None:
                missing.append("clinical")
            if micro_path is None:
                missing.append("micro")
            return DiagnosisCultureRelationshipResult(
                source_clinical_label="clinical",
                source_micro_label="micro",
                matching=MatchingSummary(0, 0, 0, 0, 0),
                categories=(),
                error_message=(
                    "Nie znaleziono plików: "
                    + ", ".join(missing)
                    + "."
                ),
            )

        clinical = load_csv(clinical_path)
        micro = load_csv(micro_path)
        return compute_diagnosis_culture_relationship(
            clinical,
            micro,
            source_clinical_label=clinical_path.name,
            source_micro_label=micro_path.name,
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
