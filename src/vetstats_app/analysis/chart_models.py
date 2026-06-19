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
    orientation: str = "vertical"
    legend_note: str = ""
    subtitle: str = ""
    secondary_values: tuple[float, ...] = ()
    box_plot_groups: tuple[tuple[float, ...], ...] = ()
    stacked_series_labels: tuple[str, ...] = ()
    stacked_series_values: tuple[tuple[float, ...], ...] = ()

    @property
    def has_data(self) -> bool:
        if self.chart_type == "histogram":
            return len(self.values) >= 2
        if self.chart_type == "box":
            return bool(self.labels) and bool(self.box_plot_groups)
        if self.chart_type == "grouped_bar":
            return (
                bool(self.labels)
                and len(self.values) == len(self.labels)
                and len(self.secondary_values) == len(self.labels)
            )
        if self.chart_type == "stacked_bar":
            return (
                bool(self.labels)
                and bool(self.stacked_series_labels)
                and bool(self.stacked_series_values)
                and all(
                    len(series) == len(self.labels)
                    for series in self.stacked_series_values
                )
                and any(
                    value > 0
                    for series in self.stacked_series_values
                    for value in series
                )
            )
        return bool(self.labels) and bool(self.values) and any(value > 0 for value in self.values)
