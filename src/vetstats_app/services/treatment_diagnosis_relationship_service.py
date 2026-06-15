from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.treatment_diagnosis_relationship import (
    TreatmentDiagnosisRelationshipResult,
    compute_treatment_diagnosis_relationship,
)


class TreatmentDiagnosisRelationshipService:
    def analyze(self) -> TreatmentDiagnosisRelationshipResult:
        clinical_path = self._resolve_clinical_path()
        if clinical_path is None:
            return TreatmentDiagnosisRelationshipResult(
                total_cases=0,
                included_cases=0,
                excluded_cases=0,
                source_label="clinical",
                categories=(),
                error_message=(
                    "Nie znaleziono pliku clinical.csv ani clinical_sterile.csv."
                ),
            )

        clinical = load_csv(clinical_path)
        return compute_treatment_diagnosis_relationship(
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
