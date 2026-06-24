from __future__ import annotations

from pathlib import Path

from dataclasses import replace

from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from vetstats_app.analysis.detailed_comparative import (
    AGE_REFERENCE_NOTE,
    AnalysisMode,
    AnalysisTarget,
    COMPUTED_AGE_COLUMN,
    DetailedComparativeState,
    build_analysis_target,
    build_group_count_summary,
    is_age_analysis_target,
)
from vetstats_app.analysis.detailed_comparative_analysis import (
    DetailedComparativeAnalysisResult,
)
from vetstats_app.services.detailed_comparative_service import DetailedComparativeService
from vetstats_app.ui.analysis.analysis_button_style import apply_compact_analysis_button_style
from vetstats_app.ui.analysis.chart_export_dialog import open_chart_export_dialog
from vetstats_app.ui.analysis.chart_widgets import exportable_charts
from vetstats_app.ui.analysis.detailed_group_widget import DetailedGroupWidget
from vetstats_app.ui.analysis.detailed_results_widgets import populate_detailed_results
from vetstats_app.ui.analysis.interpretation_panel import build_wrapped_text_label


class DetailedAnalysisSection(QWidget):
    _TABLE_PLACEHOLDER = "— wybierz tabelę —"
    _COLUMN_PLACEHOLDER = "— wybierz zmienną —"
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = DetailedComparativeService()
        self._datasets = self._service.load_datasets()
        self._state = self._service.default_state()
        self._suppress_updates = False
        self._last_result: DetailedComparativeAnalysisResult | None = None

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(12)

        intro_label = build_wrapped_text_label(
            "Zbuduj Grupę 1 i Grupę 2, wybierz zmienną do porównania, a następnie uruchom analizę."
        )
        scroll_layout.addWidget(intro_label)

        grouping_box = QGroupBox("Grupowanie")
        grouping_layout = QVBoxLayout(grouping_box)

        self._group_1_widget = DetailedGroupWidget(
            title="Grupa 1",
            default_name=self._state.group_1.default_name,
            locked_structure=False,
            list_tables=self._list_tables,
            list_columns=self._list_columns,
            list_values=self._list_values,
            on_changed=self._on_group_1_changed,
        )
        self._group_2_widget = DetailedGroupWidget(
            title="Grupa 2",
            default_name=self._state.group_2.default_name,
            locked_structure=True,
            list_tables=self._list_tables,
            list_columns=self._list_columns,
            list_values=self._list_values,
            on_changed=self._on_group_2_changed,
        )
        grouping_layout.addWidget(self._group_1_widget)
        grouping_layout.addWidget(self._group_2_widget)

        self._counts_label = build_wrapped_text_label("Liczebność grup: —")
        grouping_layout.addWidget(self._counts_label)

        scroll_layout.addWidget(grouping_box)

        analysis_box = QGroupBox("Wybór analizy")
        analysis_layout = QVBoxLayout(analysis_box)

        target_row = QHBoxLayout()
        self._target_table_combo = QComboBox()
        self._target_column_combo = QComboBox()
        self._target_mode_combo = QComboBox()
        self._target_mode_combo.addItem("Porównanie kategoryczne", AnalysisMode.CATEGORICAL)
        self._target_mode_combo.addItem("Porównanie numeryczne", AnalysisMode.NUMERIC)
        target_row.addWidget(QLabel("Tabela:"))
        target_row.addWidget(self._target_table_combo)
        target_row.addWidget(QLabel("Kolumna:"))
        target_row.addWidget(self._target_column_combo, stretch=1)
        target_row.addWidget(QLabel("Tryb:"))
        target_row.addWidget(self._target_mode_combo)
        analysis_layout.addLayout(target_row)
        self._age_note_label = build_wrapped_text_label(AGE_REFERENCE_NOTE)
        self._age_note_label.setVisible(False)
        analysis_layout.addWidget(self._age_note_label)

        scroll_layout.addWidget(analysis_box)

        action_row = QHBoxLayout()
        self._analyze_button = QPushButton("Analizuj")
        apply_compact_analysis_button_style(self._analyze_button)
        self._analyze_button.clicked.connect(self._on_analyze_clicked)
        self._export_pdf_button = QPushButton("Eksportuj raport PDF")
        apply_compact_analysis_button_style(self._export_pdf_button)
        self._export_pdf_button.setEnabled(False)
        self._export_pdf_button.clicked.connect(self._on_export_pdf_clicked)
        self._export_charts_button = QPushButton("Eksport wykresów")
        apply_compact_analysis_button_style(self._export_charts_button)
        self._export_charts_button.setEnabled(False)
        self._export_charts_button.clicked.connect(self._on_export_charts_clicked)
        action_row.addWidget(self._analyze_button)
        action_row.addWidget(self._export_pdf_button)
        action_row.addWidget(self._export_charts_button)
        action_row.addStretch()
        scroll_layout.addLayout(action_row)

        self._status_label = build_wrapped_text_label("")
        scroll_layout.addWidget(self._status_label)

        self._results_group_description = self._build_results_placeholder(
            "Opis grup",
        )
        self._results_descriptive = self._build_results_placeholder(
            "Statystyka opisowa",
        )
        self._results_statistical = self._build_results_placeholder(
            "Analiza statystyczna",
        )
        self._results_charts = self._build_results_placeholder("Wykresy")
        scroll_layout.addWidget(self._results_group_description)
        scroll_layout.addWidget(self._results_descriptive)
        scroll_layout.addWidget(self._results_statistical)
        scroll_layout.addWidget(self._results_charts)
        scroll_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll_area)

        self._target_table_combo.currentTextChanged.connect(self._on_target_table_changed)
        self._target_column_combo.currentTextChanged.connect(self._on_target_changed)
        self._target_mode_combo.currentIndexChanged.connect(self._on_target_changed)

        self._reload_target_tables()
        self._sync_ui_from_state()

    def _build_results_placeholder(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.addWidget(
            build_wrapped_text_label(
                "Sekcja przygotowana — wyniki pojawią się po uruchomieniu analizy statystycznej."
            )
        )
        return box

    def _list_tables(self) -> tuple[str, ...]:
        return self._service.list_tables(self._datasets)

    def _list_columns(self, table_name: str) -> tuple[str, ...]:
        return self._service.list_columns(table_name, self._datasets)

    def _list_values(self, table_name: str, column_name: str) -> tuple[str, ...]:
        return self._service.list_values(table_name, column_name, self._datasets)

    def _on_group_1_changed(self) -> None:
        if self._suppress_updates:
            return
        self._state = replace(self._state, group_1=self._group_1_widget.get_group())
        self._state = self._service.mirror_group_2(self._state)
        self._sync_ui_from_state()

    def _on_group_2_changed(self) -> None:
        if self._suppress_updates:
            return
        self._state = replace(self._state, group_2=self._group_2_widget.get_group())
        self._refresh_validation_ui()

    def _on_target_table_changed(self, _table_name: str) -> None:
        if self._suppress_updates:
            return
        table_name = self._selected_target_table()
        self._populate_target_column_combo(table_name)
        self._on_target_changed()

    def _on_target_changed(self) -> None:
        if self._suppress_updates:
            return
        self._state = replace(
            self._state,
            analysis_target=self._build_analysis_target_from_ui(),
        )
        target = self._state.analysis_target
        if not target.is_complete():
            self._age_note_label.setVisible(False)
            self._target_mode_combo.setEnabled(True)
            self._refresh_validation_ui()
            return

        if is_age_analysis_target(target):
            mode_index = self._target_mode_combo.findData(AnalysisMode.NUMERIC)
            if mode_index >= 0:
                self._target_mode_combo.setCurrentIndex(mode_index)
            self._target_mode_combo.setEnabled(False)
        else:
            self._target_mode_combo.setEnabled(True)

        self._age_note_label.setVisible(is_age_analysis_target(target))
        self._refresh_validation_ui()

    def _on_analyze_clicked(self) -> None:
        self._state = self._collect_state_from_ui()
        validation = self._service.validate(self._state, self._datasets)
        if not validation.can_analyze:
            messages: list[str] = []
            messages.extend(validation.blocking_messages)
            messages.extend(validation.warning_messages)
            self._status_label.setText("\n".join(messages) or validation.status_message)
            return

        result = self._service.analyze(self._state, self._datasets)
        if not result.is_success:
            self._last_result = None
            self._update_export_actions(None)
            self._status_label.setText(result.error_message or "Analiza nie powiodła się.")
            return

        self._last_result = result
        self._update_export_actions(result)

        populate_detailed_results(
            group_description_box=self._results_group_description,
            descriptive_box=self._results_descriptive,
            statistical_box=self._results_statistical,
            charts_box=self._results_charts,
            result=result,
        )

        status_lines = ["Analiza zakończona."]
        status_lines.extend(validation.warning_messages)
        self._status_label.setText("\n".join(status_lines))

    def _update_export_actions(
        self,
        result: DetailedComparativeAnalysisResult | None,
    ) -> None:
        has_result = result is not None and result.is_success
        self._export_pdf_button.setEnabled(has_result)
        charts_available = bool(exportable_charts(result.charts)) if has_result else False
        self._export_charts_button.setEnabled(charts_available)

    def _on_export_charts_clicked(self) -> None:
        if self._last_result is None or not self._last_result.is_success:
            return
        open_chart_export_dialog(self, self._last_result.charts)

    def _on_export_pdf_clicked(self) -> None:
        if self._last_result is None or not self._last_result.is_success:
            return

        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Eksportuj raport PDF",
            "analiza_szczegolowa.pdf",
            "Pliki PDF (*.pdf)",
        )
        if not destination:
            return

        error_message = self._service.export_report_pdf(
            self._last_result,
            Path(destination),
        )
        if error_message:
            QMessageBox.warning(self, "Eksportuj raport PDF", error_message)
            return

        QMessageBox.information(
            self,
            "Eksportuj raport PDF",
            f"Raport PDF zapisano w:\n{destination}",
        )

    def _sync_ui_from_state(self) -> None:
        self._suppress_updates = True
        try:
            self._group_1_widget.set_group(self._state.group_1)
            self._group_2_widget.set_group(self._state.group_2)
            self._group_1_widget.refresh_dynamic_options()
            self._group_2_widget.refresh_dynamic_options()

            target = self._state.analysis_target
            if target.table_name:
                table_index = self._target_table_combo.findData(target.table_name)
                if table_index >= 0:
                    self._target_table_combo.setCurrentIndex(table_index)
            else:
                self._target_table_combo.setCurrentIndex(0)

            self._populate_target_column_combo(self._selected_target_table())
            if target.column_name:
                column_index = self._target_column_combo.findData(target.column_name)
                if column_index >= 0:
                    self._target_column_combo.setCurrentIndex(column_index)
            else:
                self._target_column_combo.setCurrentIndex(0)

            mode_index = self._target_mode_combo.findData(target.mode)
            if mode_index >= 0:
                self._target_mode_combo.setCurrentIndex(mode_index)
            self._target_mode_combo.setEnabled(
                not is_age_analysis_target(target) if target.is_complete() else True
            )
            self._age_note_label.setVisible(is_age_analysis_target(target))
        finally:
            self._suppress_updates = False
        self._refresh_validation_ui()

    def _reload_target_tables(self) -> None:
        self._target_table_combo.blockSignals(True)
        self._target_table_combo.clear()
        self._target_table_combo.addItem(self._TABLE_PLACEHOLDER, "")
        for table_name in self._list_tables():
            self._target_table_combo.addItem(table_name, table_name)
        self._target_table_combo.setCurrentIndex(0)
        self._target_table_combo.blockSignals(False)
        self._populate_target_column_combo("")

    def _populate_target_column_combo(self, table_name: str) -> None:
        self._target_column_combo.blockSignals(True)
        self._target_column_combo.clear()
        self._target_column_combo.addItem(self._COLUMN_PLACEHOLDER, "")
        if table_name:
            for column_id, display_label in self._service.list_target_columns(
                table_name,
                self._datasets,
            ):
                self._target_column_combo.addItem(display_label, column_id)
        self._target_column_combo.setCurrentIndex(0)
        self._target_column_combo.blockSignals(False)

    def _selected_target_table(self) -> str:
        return self._combo_item_key(self._target_table_combo)

    def _selected_target_column(self) -> str:
        return self._combo_item_key(self._target_column_combo)

    def _combo_item_key(self, combo: QComboBox) -> str:
        data = combo.currentData()
        if isinstance(data, str) and data:
            return data
        text = combo.currentText().strip()
        if not text or text in {self._TABLE_PLACEHOLDER, self._COLUMN_PLACEHOLDER}:
            return ""
        for index in range(combo.count()):
            if combo.itemText(index).strip() == text:
                item_data = combo.itemData(index)
                if isinstance(item_data, str) and item_data:
                    return item_data
        return text

    def _build_analysis_target_from_ui(self) -> AnalysisTarget:
        return build_analysis_target(
            self._selected_target_table(),
            self._selected_target_column(),
            self._target_mode_combo.currentData(),
        )

    def _collect_state_from_ui(self) -> DetailedComparativeState:
        return DetailedComparativeState(
            group_1=self._group_1_widget.get_group(),
            group_2=self._group_2_widget.get_group(),
            analysis_target=self._build_analysis_target_from_ui(),
        )

    def collect_state_for_full_report(self) -> DetailedComparativeState:
        return self._collect_state_from_ui()

    def last_result(self) -> DetailedComparativeAnalysisResult | None:
        return self._last_result

    def _refresh_validation_ui(self) -> None:
        validation = self._service.validate(self._state, self._datasets)
        group_1_summary = build_group_count_summary(
            group_name=self._state.group_1.display_name,
            patient_count=validation.group_1_count,
            total_patient_count=validation.total_patient_count,
        )
        group_2_summary = build_group_count_summary(
            group_name=self._state.group_2.display_name,
            patient_count=validation.group_2_count,
            total_patient_count=validation.total_patient_count,
        )
        counts_text = (
            f"{group_1_summary.group_name}: n = {group_1_summary.patient_count}"
        )
        if group_1_summary.share_percent is not None:
            counts_text += f" ({group_1_summary.share_percent:.1f}% zbioru)"
        counts_text += (
            f" | {group_2_summary.group_name}: n = {group_2_summary.patient_count}"
        )
        if group_2_summary.share_percent is not None:
            counts_text += f" ({group_2_summary.share_percent:.1f}% zbioru)"
        if validation.total_patient_count:
            counts_text += f" | Pacjenci w zbiorze: {validation.total_patient_count}"
        self._counts_label.setText(counts_text)

        messages: list[str] = []
        messages.extend(validation.blocking_messages)
        messages.extend(validation.warning_messages)
        if not messages and validation.can_analyze:
            messages.append(validation.status_message)
        self._status_label.setText("\n".join(messages))
        self._analyze_button.setEnabled(validation.can_analyze)
