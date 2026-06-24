from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from vetstats_app.services.full_report_service import (
    DetailedAnalysisContext,
    FullReportService,
)
from vetstats_app.ui.report.report_metadata_panel import ReportMetadataPanel
from vetstats_app.ui.report.report_structure_panel import ReportStructurePanel


class ReportPage(QWidget):
    def __init__(
        self,
        *,
        detailed_context_provider: Callable[[], DetailedAnalysisContext] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._detailed_context_provider = detailed_context_provider
        self._full_report_service = FullReportService()

        self._generate_full_report_button = QPushButton("Generuj pełny raport PDF")
        self._generate_full_report_button.clicked.connect(
            self._on_generate_full_report_clicked
        )

        self._status_label = QLabel(
            "Wygeneruj jeden dokument PDF zawierający wszystkie moduły analizy "
            "automatycznej oraz bieżącą analizę szczegółową."
        )
        self._status_label.setWordWrap(True)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)

        action_bar = QHBoxLayout()
        action_bar.addWidget(self._generate_full_report_button)
        action_bar.addStretch()

        report_metadata_panel = ReportMetadataPanel()
        report_structure_panel = ReportStructurePanel()

        layout = QVBoxLayout(self)
        layout.addLayout(action_bar)
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress_bar)
        layout.addWidget(report_metadata_panel)
        layout.addWidget(report_structure_panel, stretch=1)

    def _on_generate_full_report_clicked(self) -> None:
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Generuj pełny raport PDF",
            "vetstats_pelny_raport.pdf",
            "Pliki PDF (*.pdf)",
        )
        if not destination:
            return

        detailed_context = None
        if self._detailed_context_provider is not None:
            detailed_context = self._detailed_context_provider()

        self._set_busy(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)

        def _progress(section_name: str, index: int, total: int) -> None:
            percent = int((index / max(total, 1)) * 100)
            self._progress_bar.setValue(percent)
            self._status_label.setText(
                f"Generowanie raportu ({index}/{total}): {section_name}…"
            )
            QApplication.processEvents()

        error_message, warnings = self._full_report_service.export_full_report_pdf(
            Path(destination),
            detailed_context=detailed_context,
            progress_callback=_progress,
        )

        self._set_busy(False)
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)

        if error_message:
            self._status_label.setText(error_message)
            QMessageBox.warning(self, "Generuj pełny raport PDF", error_message)
            return

        success_text = f"Pełny raport PDF zapisano w:\n{destination}"
        if warnings:
            success_text += (
                "\n\nUwagi:\n"
                + "\n".join(f"• {warning}" for warning in warnings)
            )
        self._status_label.setText(f"Raport zapisano: {destination}")
        QMessageBox.information(self, "Generuj pełny raport PDF", success_text)

    def _set_busy(self, busy: bool) -> None:
        self._generate_full_report_button.setEnabled(not busy)
