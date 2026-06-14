"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from data_sterilizer.config import SterilizerPaths

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_INPUT_DIR = PROJECT_ROOT / "Data_to_check"


@pytest.fixture
def sample_paths() -> SterilizerPaths:
    return SterilizerPaths(
        input_dir=SAMPLE_INPUT_DIR,
        output_dir=PROJECT_ROOT / "Sterile_data",
        reports_dir=PROJECT_ROOT / "reports",
    )
