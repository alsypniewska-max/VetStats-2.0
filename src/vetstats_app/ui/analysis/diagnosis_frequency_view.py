from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

MODULE_TITLE = "Analiza częstości rozpoznań"

DIAGNOSIS_CODE_MAPPING = [
    ("s", "stromal"),
    ("e", "epithelial"),
    ("p", "perforative"),
    ("n", "neurotrophic"),
    ("m", "melting"),
    ("sceed", "SCEED"),
    ("x", "other (non ulcer)"),
]


class DiagnosisFrequencyView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        module_title = QLabel(MODULE_TITLE)

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")

        action_bar = QHBoxLayout()
        action_bar.addWidget(generate_report_button)
        action_bar.addWidget(export_charts_button)
        action_bar.addStretch()

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(
            QLabel(
                "Moduł przedstawia analizę częstości rozpoznań na podstawie tabeli "
                "clinical oraz pola type_of_ulcer."
            )
        )
        content_layout.addWidget(summary_group)

        mapping_group = QGroupBox("Mapowanie kodów rozpoznań")
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_table = QTableWidget()
        mapping_table.setColumnCount(2)
        mapping_table.setHorizontalHeaderLabels(["Kod", "Rozpoznanie"])
        mapping_table.setRowCount(len(DIAGNOSIS_CODE_MAPPING))
        mapping_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        mapping_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        mapping_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        mapping_table.setSortingEnabled(False)
        mapping_table.horizontalHeader().setSortIndicatorShown(False)
        mapping_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for row, (code, diagnosis) in enumerate(DIAGNOSIS_CODE_MAPPING):
            mapping_table.setItem(row, 0, QTableWidgetItem(code))
            mapping_table.setItem(row, 1, QTableWidgetItem(diagnosis))
        mapping_layout.addWidget(mapping_table)
        content_layout.addWidget(mapping_group)

        frequency_group = QGroupBox("Częstość rozpoznań")
        frequency_layout = QVBoxLayout(frequency_group)
        frequency_layout.addWidget(
            QLabel("Placeholder: tabela z liczbą wystąpień poszczególnych rozpoznań.")
        )
        content_layout.addWidget(frequency_group)

        chart_group = QGroupBox("Wykres częstości")
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.addWidget(
            QLabel("Placeholder: wykres częstości rozpoznań.")
        )
        content_layout.addWidget(chart_group)

        interpretation_group = QGroupBox("Interpretacja")
        interpretation_layout = QVBoxLayout(interpretation_group)
        interpretation_layout.addWidget(
            QLabel(
                "Placeholder: moduł podsumuje najczęstsze i najrzadsze kategorie rozpoznań."
            )
        )
        content_layout.addWidget(interpretation_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(module_title)
        layout.addLayout(action_bar)
        layout.addWidget(scroll_area, stretch=1)
