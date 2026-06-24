from __future__ import annotations

from pathlib import Path

import pandas as pd

from vetstats_app.analysis.detailed_comparative import (
    DetailedComparativeState,
    DetailedComparativeValidation,
    default_detailed_comparative_state,
    list_analysis_target_columns,
    list_columns_for_table,
    list_distinct_column_values,
    list_table_names,
    mirror_group_2_structure,
    resolve_group_patient_ids,
    validate_detailed_comparative_state,
)
from vetstats_app.analysis.detailed_comparative_analysis import (
    DetailedComparativeAnalysisResult,
    run_detailed_comparative_analysis,
)
from vetstats_app.services.detailed_comparative_report_pdf import (
    write_detailed_comparative_report_pdf,
)
from vetstats_app.services.preview_data_service import PreviewDataService


class DetailedComparativeService:
    def __init__(self, preview_service: PreviewDataService | None = None) -> None:
        self._preview_service = preview_service or PreviewDataService()

    def load_datasets(self) -> dict[str, pd.DataFrame]:
        snapshots = self._preview_service.load_all()
        datasets: dict[str, pd.DataFrame] = {}
        for table_name, snapshot in snapshots.items():
            if snapshot.is_loaded and snapshot.frame is not None:
                datasets[table_name] = snapshot.frame
        return datasets

    def default_state(self) -> DetailedComparativeState:
        return default_detailed_comparative_state()

    def mirror_group_2(
        self,
        state: DetailedComparativeState,
    ) -> DetailedComparativeState:
        return DetailedComparativeState(
            group_1=state.group_1,
            group_2=mirror_group_2_structure(state.group_1, state.group_2),
            analysis_target=state.analysis_target,
        )

    def validate(
        self,
        state: DetailedComparativeState,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> DetailedComparativeValidation:
        data = datasets if datasets is not None else self.load_datasets()
        return validate_detailed_comparative_state(data, state)

    def list_tables(self, datasets: dict[str, pd.DataFrame] | None = None) -> tuple[str, ...]:
        data = datasets if datasets is not None else self.load_datasets()
        return list_table_names(data)

    def list_columns(
        self,
        table_name: str,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> tuple[str, ...]:
        data = datasets if datasets is not None else self.load_datasets()
        return list_columns_for_table(data, table_name)

    def list_target_columns(
        self,
        table_name: str,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> tuple[tuple[str, str], ...]:
        data = datasets if datasets is not None else self.load_datasets()
        return list_analysis_target_columns(data, table_name)

    def list_values(
        self,
        table_name: str,
        column_name: str,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> tuple[str, ...]:
        data = datasets if datasets is not None else self.load_datasets()
        return list_distinct_column_values(data, table_name, column_name)

    def resolve_group_ids(
        self,
        state: DetailedComparativeState,
        *,
        group_index: int,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> set[str]:
        data = datasets if datasets is not None else self.load_datasets()
        group = state.group_1 if group_index == 1 else state.group_2
        return resolve_group_patient_ids(data, group)

    def analyze(
        self,
        state: DetailedComparativeState,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> DetailedComparativeAnalysisResult:
        data = datasets if datasets is not None else self.load_datasets()
        return run_detailed_comparative_analysis(data, state)

    def export_report_pdf(
        self,
        result: DetailedComparativeAnalysisResult,
        destination: Path,
    ) -> str | None:
        if not result.is_success:
            return result.error_message or "Brak wyników analizy do eksportu."
        try:
            write_detailed_comparative_report_pdf(result, destination)
        except OSError as exc:
            return f"Nie udało się zapisać raportu PDF: {exc}"
        except Exception as exc:
            return f"Nie udało się wygenerować raportu PDF: {exc}"
        return None
