"""Tests for type_of_surgery mapping used in procedure–diagnosis analysis."""

from __future__ import annotations

from vetstats_app.analysis.procedure_diagnosis_relationship import (
    normalize_procedure_codes,
    procedure_display_label,
)


def test_normalize_procedure_codes_accepts_new_surgery_values() -> None:
    assert normalize_procedure_codes("deb") == ("deb",)
    assert normalize_procedure_codes("debkol") == ("debkol",)
    assert normalize_procedure_codes("kol") == ("kol",)
    assert normalize_procedure_codes("deb;kol") == ("deb", "kol")


def test_procedure_display_label_for_new_surgery_values() -> None:
    assert procedure_display_label("deb") == "debridement"
    assert procedure_display_label("debkol") == "debridement + soczewka kolagenowa"
    assert procedure_display_label("kol") == "soczewka kolagenowa"
