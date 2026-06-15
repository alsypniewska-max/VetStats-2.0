from vetstats_app.ui.analysis.automatic_module_page import AutomaticModulePage, text_section

MODULE_TITLE = "Analiza oporności bakterii w czasie"


class ResistanceOverTimeView(AutomaticModulePage):
    def __init__(self, parent=None) -> None:
        super().__init__(
            MODULE_TITLE,
            [
                text_section(
                    "Podsumowanie",
                    "Moduł przedstawia oporność bakterii w czasie wyłącznie "
                    "na podstawie tabeli micro.",
                ),
                text_section(
                    "Zakres czasowy analizy",
                    "Placeholder: analiza będzie porównywać dane roczne "
                    "dla lat 2024, 2025 i 2026.",
                ),
                text_section(
                    "Kryteria włączenia danych",
                    "Placeholder: wiersze z bacteria = negative zostaną wykluczone "
                    "ze statystyk oporności w czasie.",
                ),
                text_section(
                    "Wrażliwość ogólna i gatunkowa",
                    "Placeholder: w tym miejscu pojawią się przyszłe zestawienia "
                    "ogólnego poziomu wrażliwości i oporności oraz wzorców "
                    "w podziale na gatunki bakterii — bez prezentacji "
                    "obliczonych klas, progów ani wyników liczbowych na tym etapie.",
                ),
                text_section(
                    "Zestawienia dla antybiotyków",
                    "Placeholder: moduł zapewni później podsumowania dla poszczególnych "
                    "antybiotyków oraz widoki histogramowe reakcji gatunków bakterii "
                    "na każdy antybiotyk.",
                ),
                text_section(
                    "Interpretacja",
                    "Placeholder: moduł podsumuje trendy czasowe oporności bakterii "
                    "oraz wrażliwości na antybiotyki.",
                ),
            ],
            parent,
        )
