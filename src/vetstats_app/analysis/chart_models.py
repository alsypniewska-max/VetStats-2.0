from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisChartSpec:
    chart_id: str
    title: str
    chart_type: str
    labels: tuple[str, ...]
    values: tuple[float, ...]
    x_axis_label: str = ""
    y_axis_label: str = ""

    @property
    def has_data(self) -> bool:
        return bool(self.labels) and bool(self.values) and any(value > 0 for value in self.values)
