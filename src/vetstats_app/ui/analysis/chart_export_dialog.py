from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.chart_models import AnalysisChartSpec
from vetstats_app.services.analysis_chart_renderer import create_chart_widget
from vetstats_app.services.chart_export_service import (
    ChartExportOverrides,
    ChartExportSettings,
    export_all_charts,
    export_single_chart,
)
from vetstats_app.ui.analysis.chart_widgets import exportable_charts

_FORMAT_LABELS = {
    "pdf": "PDF",
    "png": "PNG",
    "tiff": "TIFF",
}

_EDIT_DIALOG_DEFAULT_WIDTH = 920
_EDIT_DIALOG_DEFAULT_HEIGHT = 820
_EDIT_DIALOG_MIN_WIDTH = 720
_EDIT_DIALOG_MIN_HEIGHT = 680


def open_chart_export_dialog(
    parent: QWidget,
    charts: tuple[AnalysisChartSpec, ...],
) -> None:
    charts_to_export = exportable_charts(charts)
    if not charts_to_export:
        QMessageBox.information(
            parent,
            "Eksport wykresów",
            "Brak wykresów do wyeksportowania w bieżącej sekcji.",
        )
        return

    dialog = ChartExportOverviewDialog(charts_to_export, parent)
    dialog.exec()


class ChartExportSettingsPanel(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Ustawienia eksportu", parent)

        self._format_combo = QComboBox()
        for file_format, label in _FORMAT_LABELS.items():
            self._format_combo.addItem(label, file_format)

        self._dpi_combo = QComboBox()
        self._dpi_combo.addItem("300", 300)
        self._dpi_combo.addItem("600", 600)

        form = QFormLayout()
        form.addRow("Format pliku:", self._format_combo)
        form.addRow("Rozdzielczość (DPI):", self._dpi_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(form)

    def settings(self) -> ChartExportSettings:
        return ChartExportSettings(
            file_format=str(self._format_combo.currentData()),
            dpi=int(self._dpi_combo.currentData()),
        )


class ChartExportOverviewDialog(QDialog):
    def __init__(
        self,
        charts: tuple[AnalysisChartSpec, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._charts = charts

        self.setWindowTitle("Eksport wykresów")
        self.setMinimumWidth(520)

        count_label = QLabel(
            f"Liczba wygenerowanych wykresów w bieżącej sekcji: {len(charts)}"
        )

        titles_group = QGroupBox("Automatycznie wygenerowane wykresy")
        titles_layout = QVBoxLayout(titles_group)
        titles_list = QListWidget()
        for chart in charts:
            titles_list.addItem(chart.title)
        titles_layout.addWidget(titles_list)

        self._settings_panel = ChartExportSettingsPanel()

        bulk_note = QLabel(
            "Eksportuj wszystkie: zapisuje wykresy z automatycznymi tytułami "
            "i opisami osi (bez edycji). Aby zmienić tytuł lub opisy osi, "
            "wybierz Edytuj."
        )
        bulk_note.setWordWrap(True)

        export_all_button = QPushButton("Eksportuj wszystkie")
        edit_button = QPushButton("Edytuj")
        export_all_button.clicked.connect(self._on_export_all)
        edit_button.clicked.connect(self._on_edit)

        actions = QHBoxLayout()
        actions.addWidget(export_all_button)
        actions.addWidget(edit_button)
        actions.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(count_label)
        layout.addWidget(titles_group)
        layout.addWidget(self._settings_panel)
        layout.addWidget(bulk_note)
        layout.addLayout(actions)

    def _on_export_all(self) -> None:
        settings = self._settings_panel.settings()
        destination = self._pick_export_all_destination(settings)
        if destination is None:
            return

        error_message = export_all_charts(self._charts, settings, destination)
        if error_message is not None:
            QMessageBox.warning(self, "Eksport wykresów", error_message)
            return

        if settings.file_format == "pdf":
            success_text = f"Zapisano wszystkie wykresy do pliku PDF:\n{destination}"
        else:
            success_text = (
                f"Zapisano {len(self._charts)} wykresów w formacie "
                f"{_FORMAT_LABELS[settings.file_format]} (DPI {settings.dpi}) "
                f"do katalogu:\n{destination}"
            )
        QMessageBox.information(self, "Eksport wykresów", success_text)
        self.accept()

    def _on_edit(self) -> None:
        settings = self._settings_panel.settings()
        for index, chart in enumerate(self._charts, start=1):
            edit_dialog = ChartExportEditDialog(
                chart,
                chart_index=index,
                chart_count=len(self._charts),
                settings=settings,
                parent=self,
            )
            if edit_dialog.exec() != QDialog.DialogCode.Accepted:
                return

        QMessageBox.information(
            self,
            "Eksport wykresów",
            f"Zapisano {len(self._charts)} wykresów "
            f"w formacie {_FORMAT_LABELS[settings.file_format]} (DPI {settings.dpi}).",
        )
        self.accept()

    def _pick_export_all_destination(
        self,
        settings: ChartExportSettings,
    ) -> Path | None:
        if settings.file_format == "pdf":
            destination, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "Eksportuj wszystkie wykresy",
                "wykresy_sekcji.pdf",
                "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
            )
            if not destination:
                return None
            return Path(destination)

        directory = QFileDialog.getExistingDirectory(
            self,
            "Wybierz katalog na wykresy",
        )
        if not directory:
            return None
        return Path(directory)


class ChartExportEditDialog(QDialog):
    def __init__(
        self,
        chart: AnalysisChartSpec,
        *,
        chart_index: int,
        chart_count: int,
        settings: ChartExportSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._chart = chart
        self._settings = settings

        self.setWindowTitle("Edycja wykresu przed eksportem")
        self.resize(_EDIT_DIALOG_DEFAULT_WIDTH, _EDIT_DIALOG_DEFAULT_HEIGHT)
        self.setMinimumSize(_EDIT_DIALOG_MIN_WIDTH, _EDIT_DIALOG_MIN_HEIGHT)

        refresh_button = QPushButton("Odśwież podgląd")
        refresh_button.clicked.connect(self._refresh_preview)

        save_and_continue_button = QPushButton("Zapisz i przejdź dalej")
        save_and_continue_button.clicked.connect(self._on_save_and_continue)

        top_actions = QHBoxLayout()
        top_actions.addWidget(refresh_button)
        top_actions.addStretch()
        top_actions.addWidget(save_and_continue_button)

        progress_label = QLabel(f"Wykres {chart_index} z {chart_count}")

        settings_info = QLabel(
            f"Format: {_FORMAT_LABELS[settings.file_format]} | DPI: {settings.dpi}"
        )

        edit_group = QGroupBox("Edycja wykresu")
        edit_form = QFormLayout(edit_group)
        self._title_field = QLineEdit(chart.title)
        self._x_axis_field = QLineEdit(chart.x_axis_label)
        self._y_axis_field = QLineEdit(chart.y_axis_label)
        edit_form.addRow("Tytuł wykresu:", self._title_field)
        edit_form.addRow("Opis osi X:", self._x_axis_field)
        edit_form.addRow("Opis osi Y:", self._y_axis_field)

        preview_group = QGroupBox("Podgląd")
        preview_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        preview_layout = QVBoxLayout(preview_group)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        preview_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._preview_container = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_container)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        self._preview_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        preview_scroll.setWidget(self._preview_container)
        preview_layout.addWidget(preview_scroll)

        layout = QVBoxLayout(self)
        layout.addLayout(top_actions)
        layout.addWidget(progress_label)
        layout.addWidget(settings_info)
        layout.addWidget(edit_group)
        layout.addWidget(preview_group, stretch=1)

        self._refresh_preview()

    def _edited_spec(self) -> AnalysisChartSpec:
        title = self._title_field.text().strip()
        return replace(
            self._chart,
            title=title if title else self._chart.title,
            x_axis_label=self._x_axis_field.text().strip(),
            y_axis_label=self._y_axis_field.text().strip(),
        )

    def _refresh_preview(self) -> None:
        while self._preview_layout.count():
            item = self._preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._preview_layout.addWidget(create_chart_widget(self._edited_spec()))

    def _on_save_and_continue(self) -> None:
        title = self._title_field.text().strip()
        if not title:
            QMessageBox.warning(self, "Edycja wykresu", "Tytuł wykresu nie może być pusty.")
            return

        overrides = ChartExportOverrides(
            title=title,
            x_axis_label=self._x_axis_field.text(),
            y_axis_label=self._y_axis_field.text(),
        )

        default_name = f"{self._chart.chart_id}.{self._settings.file_format}"
        file_filter = _save_file_filter(self._settings.file_format)
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Zapisz wykres",
            default_name,
            file_filter,
        )
        if not destination:
            return

        error_message = export_single_chart(
            self._chart,
            self._settings,
            Path(destination),
            overrides=overrides,
        )
        if error_message is not None:
            QMessageBox.warning(self, "Edycja wykresu", error_message)
            return

        self.accept()


def _save_file_filter(file_format: str) -> str:
    if file_format == "pdf":
        return "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)"
    if file_format == "png":
        return "Pliki PNG (*.png);;Wszystkie pliki (*.*)"
    return "Pliki TIFF (*.tif *.tiff);;Wszystkie pliki (*.*)"
