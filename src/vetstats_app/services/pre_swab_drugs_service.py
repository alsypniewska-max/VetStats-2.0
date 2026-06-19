from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.clinical_micro_matching import ClinicalMicroMatchingSummary
from vetstats_app.analysis.pre_swab_drugs import PreSwabDrugsResult, compute_pre_swab_drugs


class PreSwabDrugsService:
    def analyze(self) -> PreSwabDrugsResult:
        clinical_path = self._resolve_dataset_path("clinical.csv")
        micro_path = self._resolve_dataset_path("micro.csv")

        if clinical_path is None or micro_path is None:
            missing = []
            if clinical_path is None:
                missing.append("clinical")
            if micro_path is None:
                missing.append("micro")
            return PreSwabDrugsResult(
                source_clinical_label="clinical",
                source_micro_label="micro",
                matching=ClinicalMicroMatchingSummary(0, 0, 0, 0),
                total_clinical_rows=0,
                no_prior_treatment_count=0,
                unknown_drug_count=0,
                with_known_drugs_count=0,
                top_drugs=(),
                culture_outcomes=(),
                drug_culture_crosstab=(),
                treatment_status_culture_crosstab=(),
                error_message=(
                    "Nie znaleziono plików: " + ", ".join(missing) + "."
                ),
            )

        clinical = load_csv(clinical_path)
        micro = load_csv(micro_path)
        return compute_pre_swab_drugs(
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
