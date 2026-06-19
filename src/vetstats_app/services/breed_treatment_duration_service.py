from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.breed_treatment_duration import (
    BreedTreatmentDurationExclusions,
    BreedTreatmentDurationResult,
    compute_breed_treatment_duration,
)


class BreedTreatmentDurationService:
    def analyze(self) -> BreedTreatmentDurationResult:
        clinical_path = self._resolve_dataset_path("clinical.csv")
        patient_path = self._resolve_dataset_path("patient.csv")

        if clinical_path is None or patient_path is None:
            missing = []
            if clinical_path is None:
                missing.append("clinical")
            if patient_path is None:
                missing.append("patient")
            return BreedTreatmentDurationResult(
                source_clinical_label="clinical",
                source_patient_label="patient",
                exclusions=BreedTreatmentDurationExclusions(
                    total_clinical_rows=0,
                    excluded_non_ulcer=0,
                    excluded_not_good=0,
                    excluded_enucleation=0,
                    excluded_no_followup=0,
                    excluded_continuation=0,
                    excluded_duration_unavailable=0,
                    included_healed_with_duration=0,
                    excluded_unknown_species=0,
                    excluded_unknown_breed=0,
                    included_with_known_species=0,
                    included_with_known_breed=0,
                ),
                dog_summary=None,
                cat_summary=None,
                dog_breeds=(),
                cat_breeds=(),
                statistical_tests=(),
                dog_duration_days=(),
                cat_duration_days=(),
                dog_breed_value_groups=(),
                cat_breed_value_groups=(),
                error_message=(
                    "Nie znaleziono plików: " + ", ".join(missing) + "."
                ),
            )

        clinical = load_csv(clinical_path)
        patient = load_csv(patient_path)
        return compute_breed_treatment_duration(
            clinical,
            patient,
            source_clinical_label=clinical_path.name,
            source_patient_label=patient_path.name,
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
