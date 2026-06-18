from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_sterilizer.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, sterile_output_name
from data_sterilizer.io.loader import SOURCE_ROW_COLUMN, load_csv
from vetstats_app.services.app_event_logger import log_error, log_info, log_warning

TABLE_FILE_NAMES: dict[str, str] = {
    "patient": "patient.csv",
    "clinical": "clinical.csv",
    "micro": "micro.csv",
}


@dataclass(frozen=True)
class PreviewDatasetSnapshot:
    table_name: str
    file_name: str
    source_path: Path | None
    frame: pd.DataFrame | None
    error_message: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self.frame is not None and self.error_message is None

    @property
    def row_count(self) -> int:
        if self.frame is None:
            return 0
        return len(self.display_frame())

    @property
    def column_count(self) -> int:
        if self.frame is None:
            return 0
        return len(self.display_frame().columns)

    def display_frame(self) -> pd.DataFrame:
        if self.frame is None:
            return pd.DataFrame()
        if SOURCE_ROW_COLUMN in self.frame.columns:
            return self.frame.drop(columns=[SOURCE_ROW_COLUMN])
        return self.frame


class PreviewDataService:
    def load_all(self) -> dict[str, PreviewDatasetSnapshot]:
        return {
            table_name: self.load_table(table_name)
            for table_name in TABLE_FILE_NAMES
        }

    def load_table(self, table_name: str) -> PreviewDatasetSnapshot:
        file_name = TABLE_FILE_NAMES[table_name]
        source_path = self._resolve_dataset_path(file_name)
        if source_path is None:
            log_warning(
                "preview_data",
                f"Nie znaleziono tabeli {table_name} ({file_name})",
            )
            return PreviewDatasetSnapshot(
                table_name=table_name,
                file_name=file_name,
                source_path=None,
                frame=None,
                error_message=(
                    f"Nie znaleziono pliku {file_name} "
                    f"w katalogach Sterile_data ani Data_to_check."
                ),
            )

        try:
            frame = load_csv(source_path)
        except OSError as exc:
            log_error(
                "preview_data",
                f"Nie wczytano {table_name} z {source_path.name}: {exc}",
            )
            return PreviewDatasetSnapshot(
                table_name=table_name,
                file_name=file_name,
                source_path=source_path,
                frame=None,
                error_message=f"Nie udało się wczytać {source_path.name}: {exc}",
            )

        snapshot = PreviewDatasetSnapshot(
            table_name=table_name,
            file_name=file_name,
            source_path=source_path,
            frame=frame,
        )
        log_info(
            "preview_data",
            (
                f"Wczytano {table_name} z {source_path.name} "
                f"({snapshot.row_count} wierszy, {snapshot.column_count} kolumn)"
            ),
        )
        return snapshot

    def _resolve_dataset_path(self, dataset_name: str) -> Path | None:
        candidates = (
            DEFAULT_OUTPUT_DIR / sterile_output_name(dataset_name),
            DEFAULT_INPUT_DIR / dataset_name,
        )
        for path in candidates:
            if path.is_file():
                return path
        return None
