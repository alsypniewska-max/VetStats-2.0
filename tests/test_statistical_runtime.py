"""Tests for statistical runtime dependency helpers."""

from __future__ import annotations

from vetstats_app.analysis.detailed_comparative import BLOCK_SCIPY_MISSING
from vetstats_app.analysis.statistical_runtime import format_statistical_runtime_error


def test_format_statistical_runtime_error_maps_scipy_import_error() -> None:
    assert (
        format_statistical_runtime_error("No module named 'scipy'")
        == BLOCK_SCIPY_MISSING
    )
