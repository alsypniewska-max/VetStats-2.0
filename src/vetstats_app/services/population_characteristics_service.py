from __future__ import annotations

from pathlib import Path

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.population_characteristics import (
    PopulationCharacteristicsResult,
    compute_population_characteristics,
)


class PopulationCharacteristicsService:
    def analyze(self) -> PopulationCharacteristicsResult:
        patient_path = self._resolve_patient_path()
        if patient_path is None:
            return PopulationCharacteristicsResult(
                total_patients=0,
                total_records=0,
                species_count=0,
                source_label="patient",
                species_counts=(),
                dog_breed_counts=(),
                cat_breed_counts=(),
                age_years=(),
                error_message=(
                    "Nie znaleziono pliku patient.csv ani patient_sterile.csv."
                ),
            )

        patient = load_csv(patient_path)
        return compute_population_characteristics(
            patient,
            source_label=patient_path.name,
        )

    def _resolve_patient_path(self) -> Path | None:
        candidates = (
            DEFAULT_OUTPUT_DIR / sterile_output_name("patient.csv"),
            DEFAULT_INPUT_DIR / "patient.csv",
        )
        for path in candidates:
            if path.is_file():
                return path
        return None
