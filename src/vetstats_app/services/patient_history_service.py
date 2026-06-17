from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import load_csv
from vetstats_app.analysis.patient_history import (
    PatientHistoryCatalog,
    PatientHistoryDetail,
    build_patient_history_catalog,
    build_patient_history_detail,
    build_patient_history_section_report,
)
from vetstats_app.services.section_report_pdf import write_section_report_pdf


class PatientHistoryService:
    def __init__(self) -> None:
        self._patient: pd.DataFrame | None = None
        self._clinical: pd.DataFrame | None = None
        self._micro: pd.DataFrame | None = None
        self._source_labels: dict[str, str] = {}
        self._load_error: str | None = None
        self._load_datasets()

    def load_catalog(self) -> PatientHistoryCatalog:
        if self._load_error is not None:
            return PatientHistoryCatalog(
                source_labels=self._source_labels,
                patients=(),
                error_message=self._load_error,
            )
        if self._patient is None:
            return PatientHistoryCatalog(
                source_labels=self._source_labels,
                patients=(),
                error_message="Nie wczytano tabeli patient.",
            )
        return build_patient_history_catalog(
            self._patient,
            source_labels=self._source_labels,
        )

    def get_load_error(self) -> str | None:
        return self._load_error

    def get_detail(self, patient_id: str) -> PatientHistoryDetail | None:
        if (
            self._load_error is not None
            or self._patient is None
            or self._clinical is None
            or self._micro is None
        ):
            return None
        return build_patient_history_detail(
            patient_id,
            self._patient,
            self._clinical,
            self._micro,
        )

    def export_patient_history_pdf(
        self,
        detail: PatientHistoryDetail,
        destination: Path,
    ) -> str | None:
        report = build_patient_history_section_report(
            detail,
            source_labels=tuple(self._source_labels.values()),
        )
        try:
            write_section_report_pdf(report, Path(destination))
        except OSError as exc:
            return f"Nie udało się zapisać raportu PDF: {exc}"
        return None

    def _load_datasets(self) -> None:
        missing: list[str] = []
        datasets: dict[str, pd.DataFrame] = {}

        for table_name in ("patient", "clinical", "micro"):
            path = self._resolve_dataset_path(f"{table_name}.csv")
            if path is None:
                missing.append(table_name)
                continue
            datasets[table_name] = load_csv(path)
            self._source_labels[table_name] = path.name

        if missing:
            self._load_error = "Nie znaleziono plików: " + ", ".join(missing) + "."
            return

        self._patient = datasets["patient"]
        self._clinical = datasets["clinical"]
        self._micro = datasets["micro"]

    def _resolve_dataset_path(self, dataset_name: str) -> Path | None:
        candidates = (
            DEFAULT_OUTPUT_DIR / sterile_output_name(dataset_name),
            DEFAULT_INPUT_DIR / dataset_name,
        )
        for path in candidates:
            if path.is_file():
                return path
        return None
