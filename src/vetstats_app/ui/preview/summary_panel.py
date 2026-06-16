from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from vetstats_app.services.preview_data_service import PreviewDatasetSnapshot


class SummaryPanel(QWidget):
    def __init__(
        self,
        snapshots: dict[str, PreviewDatasetSnapshot],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        group = QGroupBox("Podsumowanie danych")
        group_layout = QVBoxLayout(group)

        group_layout.addWidget(QLabel("Wczytane pliki źródłowe:"))
        for table_name in ("patient", "clinical", "micro"):
            snapshot = snapshots[table_name]
            if snapshot.source_path is not None:
                source_text = f"  • {snapshot.file_name} — {snapshot.source_path}"
            else:
                source_text = f"  • {snapshot.file_name} — nie znaleziono"
            group_layout.addWidget(QLabel(source_text))

        group_layout.addWidget(QLabel("Liczba wierszy i kolumn:"))
        for table_name in ("patient", "clinical", "micro"):
            snapshot = snapshots[table_name]
            if snapshot.is_loaded:
                stats_text = (
                    f"  • {table_name}: {snapshot.row_count} wierszy, "
                    f"{snapshot.column_count} kolumn"
                )
            else:
                stats_text = f"  • {table_name}: brak danych"
            group_layout.addWidget(QLabel(stats_text))

        loaded_count = sum(1 for snapshot in snapshots.values() if snapshot.is_loaded)
        if loaded_count == len(snapshots):
            status_text = (
                f"Status: wczytano {loaded_count} z {len(snapshots)} tabel "
                f"(najpierw Sterile_data, potem Data_to_check)."
            )
        elif loaded_count == 0:
            status_text = (
                "Status: nie wczytano żadnej tabeli. "
                "Umieść pliki CSV w Sterile_data lub Data_to_check."
            )
        else:
            status_text = (
                f"Status: wczytano {loaded_count} z {len(snapshots)} tabel. "
                "Sprawdź brakujące pliki w Sterile_data lub Data_to_check."
            )
        group_layout.addWidget(QLabel(status_text))

        layout = QVBoxLayout(self)
        layout.addWidget(group)
