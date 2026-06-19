from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.chart_specs import build_ulcer_breed_treatment_duration_charts
from vetstats_app.analysis.ulcer_breed_treatment_duration import (
    MIN_DISPLAY_GROUP_SIZE,
    UlcerBreedTreatmentDurationResult,
    build_descriptive_stats_block,
    build_interpretation_summary,
    build_summary_details,
    cat_breed_ulcer_table_block,
    cat_ulcer_types_table_block,
    dog_breed_ulcer_table_block,
    dog_ulcer_types_table_block,
    exclusions_table_block,
)
from vetstats_app.services.analysis_report_service import AnalysisReportService
from vetstats_app.services.ulcer_breed_treatment_duration_service import (
    UlcerBreedTreatmentDurationService,
)
from vetstats_app.ui.analysis.chart_export_dialog import open_chart_export_dialog
from vetstats_app.ui.analysis.chart_widgets import build_chart_section
from vetstats_app.ui.analysis.interpretation_panel import (
    build_interpretation_section,
    build_wrapped_text_label,
)
from vetstats_app.ui.analysis.module_action_bar import build_module_action_bar
from vetstats_app.ui.analysis.reference_table import (
    configure_reference_table,
    finalize_reference_table,
)


def _configure_table(table: QTableWidget) -> None:
    configure_reference_table(table)
    table.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


def _finalize_table(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for column_index in range(table.columnCount()):
        header.setSectionResizeMode(
            column_index,
            QHeaderView.ResizeMode.ResizeToContents,
        )
    finalize_reference_table(table)
    total_width = table.frameWidth() * 2
    if table.verticalHeader().isVisible():
        total_width += table.verticalHeader().width()
    for column_index in range(table.columnCount()):
        total_width += table.columnWidth(column_index)
    table.setMaximumWidth(total_width)


def _table_from_block(block) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(len(block.columns))
    table.setHorizontalHeaderLabels(list(block.columns))
    table.setRowCount(len(block.rows))
    _configure_table(table)
    for row_index, row in enumerate(block.rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
    _finalize_table(table)
    return table


class UlcerBreedTreatmentDurationView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result = UlcerBreedTreatmentDurationService().analyze()
        self._report_service = AnalysisReportService()
        result = self._result

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")
        self._action_bar_widget = build_module_action_bar(
            generate_report_button,
            export_charts_button,
        )
        generate_report_button.clicked.connect(self._on_generate_report)
        export_charts_button.clicked.connect(self._on_export_charts)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            build_wrapped_text_label(
                "Moduł analizuje czas leczenia uleczonych przypadków wrzodowych "
                "według typu wrzodu i kombinacji rasa×typ wrzodu, osobno dla psów "
                "i kotów. Kategoryzacja typu wrzodu opiera się na terminal_ulcer_code."
            )
        )
        summary_layout.addWidget(build_wrapped_text_label(build_summary_details(result)))
        content_layout.addWidget(summary_group)

        stats_block = build_descriptive_stats_block(result)
        stats_group = QGroupBox(stats_block.title)
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.addWidget(_table_from_block(stats_block))
        content_layout.addWidget(stats_group)

        exclusions_block = exclusions_table_block(result)
        exclusions_group = QGroupBox(exclusions_block.title)
        exclusions_layout = QVBoxLayout(exclusions_group)
        exclusions_layout.addWidget(_table_from_block(exclusions_block))
        content_layout.addWidget(exclusions_group)

        if result.dog_ulcer_types:
            dog_ulcer_block = dog_ulcer_types_table_block(result)
            dog_ulcer_group = QGroupBox(dog_ulcer_block.title)
            dog_ulcer_layout = QVBoxLayout(dog_ulcer_group)
            dog_ulcer_layout.addWidget(
                build_wrapped_text_label(
                    "Podsumowanie według typu wrzodu obejmuje przypadki ze znanym "
                    "gatunkiem, także bez znanej rasy."
                )
            )
            dog_ulcer_layout.addWidget(_table_from_block(dog_ulcer_block))
            content_layout.addWidget(dog_ulcer_group)

        if result.cat_ulcer_types:
            cat_ulcer_block = cat_ulcer_types_table_block(result)
            cat_ulcer_group = QGroupBox(cat_ulcer_block.title)
            cat_ulcer_layout = QVBoxLayout(cat_ulcer_group)
            cat_ulcer_layout.addWidget(
                build_wrapped_text_label(
                    "Podsumowanie według typu wrzodu obejmuje przypadki ze znanym "
                    "gatunkiem, także bez znanej rasy."
                )
            )
            cat_ulcer_layout.addWidget(_table_from_block(cat_ulcer_block))
            content_layout.addWidget(cat_ulcer_group)

        if result.dog_breed_ulcer_rows:
            dog_block = dog_breed_ulcer_table_block(result)
            dog_group = QGroupBox(dog_block.title)
            dog_layout = QVBoxLayout(dog_group)
            dog_layout.addWidget(
                build_wrapped_text_label(
                    f"Uwaga: tabela obejmuje wyłącznie grupy rasa×typ wrzodu "
                    f"z co najmniej {MIN_DISPLAY_GROUP_SIZE} przypadkami."
                )
            )
            dog_layout.addWidget(_table_from_block(dog_block))
            content_layout.addWidget(dog_group)
        elif result.dog_ulcer_types:
            dog_group = QGroupBox(
                f"Czas leczenia według rasy i typu wrzodu — psy "
                f"(tylko grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
            )
            dog_layout = QVBoxLayout(dog_group)
            dog_layout.addWidget(
                build_wrapped_text_label(
                    f"Brak grup rasa×typ wrzodu do wyświetlenia dla psów: żadna "
                    f"kombinacja ze znaną rasą nie osiągnęła progu "
                    f"n≥{MIN_DISPLAY_GROUP_SIZE} lub brak przypadków ze znaną rasą."
                )
            )
            content_layout.addWidget(dog_group)

        if result.cat_breed_ulcer_rows:
            cat_block = cat_breed_ulcer_table_block(result)
            cat_group = QGroupBox(cat_block.title)
            cat_layout = QVBoxLayout(cat_group)
            cat_layout.addWidget(
                build_wrapped_text_label(
                    f"Uwaga: tabela obejmuje wyłącznie grupy rasa×typ wrzodu "
                    f"z co najmniej {MIN_DISPLAY_GROUP_SIZE} przypadkami."
                )
            )
            cat_layout.addWidget(_table_from_block(cat_block))
            content_layout.addWidget(cat_group)
        elif result.cat_ulcer_types:
            cat_group = QGroupBox(
                f"Czas leczenia według rasy i typu wrzodu — koty "
                f"(tylko grupy n≥{MIN_DISPLAY_GROUP_SIZE})"
            )
            cat_layout = QVBoxLayout(cat_group)
            cat_layout.addWidget(
                build_wrapped_text_label(
                    f"Brak grup rasa×typ wrzodu do wyświetlenia dla kotów: żadna "
                    f"kombinacja ze znaną rasą nie osiągnęła progu "
                    f"n≥{MIN_DISPLAY_GROUP_SIZE} lub brak przypadków ze znaną rasą."
                )
            )
            content_layout.addWidget(cat_group)

        chart_group = build_chart_section(
            "Wykresy",
            build_ulcer_breed_treatment_duration_charts(result),
            empty_message="Brak danych do wygenerowania wykresów.",
        )
        content_layout.addWidget(chart_group)
        content_layout.addWidget(
            build_interpretation_section(build_interpretation_summary(result))
        )

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area, stretch=1)

    def action_bar_widget(self) -> QWidget:
        return self._action_bar_widget

    def _on_generate_report(self) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Generuj raport",
            "ulcer_breed_treatment_duration_report.pdf",
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not destination:
            return
        error_message = self._report_service.export_ulcer_breed_treatment_duration_report_pdf(
            self._result,
            Path(destination),
        )
        if error_message is not None:
            QMessageBox.warning(self, "Generuj raport", error_message)
            return
        QMessageBox.information(
            self,
            "Generuj raport",
            f"Zapisano raport PDF do pliku:\n{destination}",
        )

    def _on_export_charts(self) -> None:
        open_chart_export_dialog(
            self,
            build_ulcer_breed_treatment_duration_charts(self._result),
        )
