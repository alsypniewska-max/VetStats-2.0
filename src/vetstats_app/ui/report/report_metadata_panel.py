from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from vetstats_app.services.analysis_report_service import resolve_dataset_label

SECTION_TITLE = "VetStats 2.0 — pełny raport analizy"


class ReportMetadataPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        group = QGroupBox("Metadane raportu")
        group_layout = QVBoxLayout(group)

        group_layout.addWidget(QLabel(f"Tytuł raportu: {SECTION_TITLE}"))
        group_layout.addWidget(QLabel("Tytuł strony: Raport analizy"))
        group_layout.addWidget(
            QLabel(
                "Źródło danych: "
                f"{resolve_dataset_label()}"
            )
        )
        group_layout.addWidget(
            QLabel(
                "Filtry: zgodnie z regułami poszczególnych modułów analizy automatycznej "
                "oraz bieżącą konfiguracją analizy szczegółowej."
            )
        )

        layout = QVBoxLayout(self)
        layout.addWidget(group)
