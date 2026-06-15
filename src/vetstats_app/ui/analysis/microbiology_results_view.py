from vetstats_app.ui.analysis.automatic_module_page import AutomaticModulePage, text_section

MODULE_TITLE = "Analiza wyników mikrobiologicznych"


class MicrobiologyResultsView(AutomaticModulePage):
    def __init__(self, parent=None) -> None:
        super().__init__(
            MODULE_TITLE,
            [
                text_section(
                    "Podsumowanie",
                    "Moduł przedstawia wyniki mikrobiologiczne w powiązaniu "
                    "z kategoriami wrzodów.",
                ),
                text_section(
                    "Najczęściej izolowane bakterie i wyniki negatywne",
                    "Placeholder: w tym miejscu pojawi się podsumowanie najczęściej "
                    "izolowanych bakterii oraz wyników negatywnych. "
                    "Wyniki negatywne będą traktowane jako prawidłowa kategoria analityczna, "
                    "a nie jako brak danych — bez prezentacji rzeczywistych wyników na tym etapie.",
                ),
                text_section(
                    "Powiązanie z typem wrzodu",
                    "Placeholder: wyniki mikrobiologiczne będą analizowane łącznie "
                    "z polem type_of_ulcer z tabeli clinical. "
                    "Jeśli type_of_ulcer = x, zostanie to potraktowane jako kategoria other. "
                    "Wiersze z nieprawidłowymi lub wykluczonymi kodami wrzodów "
                    "zostaną wyłączone z tej analizy.",
                ),
                text_section(
                    "Dopasowanie wyniku mikrobiologicznego do wizyty",
                    "Placeholder: jeśli pacjent ma wiele wyników mikrobiologicznych, "
                    "do analizy zostanie dopasowany wynik, którego date_collect "
                    "jest najbliższe date_appointment_first_before_micro.",
                ),
                text_section(
                    "Interpretacja",
                    "Placeholder: moduł podsumuje rozkład wyników mikrobiologicznych "
                    "oraz ich powiązanie z kategoriami wrzodów.",
                ),
            ],
            parent,
        )
