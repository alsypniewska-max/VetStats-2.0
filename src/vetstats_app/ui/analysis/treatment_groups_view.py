from vetstats_app.ui.analysis.automatic_module_page import AutomaticModulePage, text_section

MODULE_TITLE = "Analiza leczenia w grupach pacjentów"


class TreatmentGroupsView(AutomaticModulePage):
    def __init__(self, parent=None) -> None:
        super().__init__(
            MODULE_TITLE,
            [
                text_section(
                    "Podsumowanie",
                    "Moduł przedstawia analizę wzorców leczenia na podstawie wierszy "
                    "z tabeli clinical.",
                ),
                text_section(
                    "Podział przypadków według typu leczenia",
                    "Placeholder: tabela z podziałem przypadków według kategorii "
                    "farmacology_surgery. "
                    "f = tylko farmakologia, s = farmakologia + chirurgia.",
                ),
                text_section(
                    "Leczenie miejscowe i ogólne",
                    "Placeholder: w tym miejscu pojawi się analiza wzorców leczenia "
                    "miejscowego i ogólnego na podstawie pola topical_systemic. "
                    "Pole topical_systemic będzie mogło wskazywać leczenie miejscowe, "
                    "ogólne lub łączone — bez prezentacji rzeczywistych wyników na tym etapie.",
                ),
                text_section(
                    "Skuteczność leczenia wrzodów",
                    "Placeholder: porównanie skuteczności leczenia przypadków wrzodów. "
                    "W statystykach skuteczności leczenia wykluczone zostaną wiersze "
                    "z how_ended = continuation.",
                ),
                text_section(
                    "Interpretacja",
                    "Placeholder: moduł podsumuje najczęstsze wzorce leczenia "
                    "oraz ogólny obraz wyników leczenia.",
                ),
            ],
            parent,
        )
