"""Cleaning correction tracking for PDF reporting."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Correction:
    dataset: str
    message: str


@dataclass
class CleaningReport:
    corrections: list[Correction] = field(default_factory=list)

    def add(self, correction: Correction) -> None:
        self.corrections.append(correction)

    def extend(self, other: CleaningReport) -> None:
        self.corrections.extend(other.corrections)
