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

MODULE_TITLE = "Charakterystyka populacji pacjentów"

BASIC_COUNTS = [
    ("Liczba pacjentów", "120"),
    ("Liczba rekordów", "340"),
    ("Liczba gatunków", "4"),
]


class PopulationCharacteristicsView(QWidget):
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
                "Ta sekcja przedstawia ogólną charakterystykę populacji pacjentów "
                "na podstawie wczytanych danych."
            )
        )
        content_layout.addWidget(summary_group)

        counts_group = QGroupBox("Podstawowe liczby")
        counts_layout = QVBoxLayout(counts_group)
        counts_table = QTableWidget()
        counts_table.setColumnCount(2)
        counts_table.setHorizontalHeaderLabels(["Metryka", "Wartość"])
        counts_table.setRowCount(len(BASIC_COUNTS))
        counts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        counts_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for row, (metric, value) in enumerate(BASIC_COUNTS):
            counts_table.setItem(row, 0, QTableWidgetItem(metric))
            counts_table.setItem(row, 1, QTableWidgetItem(value))
        counts_layout.addWidget(counts_table)
        content_layout.addWidget(counts_group)

        species_chart_group = QGroupBox("Wykres: gatunki")
        species_chart_layout = QVBoxLayout(species_chart_group)
        species_chart_layout.addWidget(
            QLabel("Placeholder: wykres rozkładu gatunków w populacji pacjentów.")
        )
        content_layout.addWidget(species_chart_group)

        breed_chart_group = QGroupBox("Wykres: rasy w obrębie gatunku")
        breed_chart_layout = QVBoxLayout(breed_chart_group)
        breed_chart_layout.addWidget(
            QLabel(
                "Placeholder: wykres rozkładu ras w obrębie wybranego gatunku. "
                "Analiza ras jest prezentowana w kontekście gatunku, "
                "a nie globalnie dla wszystkich zwierząt."
            )
        )
        content_layout.addWidget(breed_chart_group)

        interpretation_group = QGroupBox("Interpretacja")
        interpretation_layout = QVBoxLayout(interpretation_group)
        interpretation_layout.addWidget(
            QLabel(
                "Placeholder: krótka interpretacja opisowa charakterystyki populacji, "
                "uwzględniająca rozkład gatunków oraz ras w obrębie poszczególnych gatunków."
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
