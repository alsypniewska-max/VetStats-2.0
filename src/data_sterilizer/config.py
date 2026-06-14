"""Shared configuration for the Data Sterilizer CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent

DATE_FORMAT = "dd.mm.yyyy"
CSV_DELIMITER = ";"
CSV_ENCODING = "utf-8"

INPUT_FILE_NAMES: tuple[str, ...] = ("patient.csv", "clinical.csv", "micro.csv")
STERILE_SUFFIX = "_sterile"


def sterile_output_name(input_file_name: str) -> str:
    """Return the cleaned output filename for a given input CSV name."""
    if not input_file_name.endswith(".csv"):
        raise ValueError(f"Expected a .csv input filename, got: {input_file_name}")
    stem = input_file_name[:-4]
    return f"{stem}{STERILE_SUFFIX}.csv"


OUTPUT_FILE_NAMES: tuple[str, ...] = tuple(
    sterile_output_name(name) for name in INPUT_FILE_NAMES
)

DEFAULT_INPUT_DIR = PROJECT_ROOT / "Data_to_check"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Sterile_data"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(frozen=True)
class SterilizerPaths:
    """Runtime paths for a single sterilizer run."""

    input_dir: Path
    output_dir: Path
    reports_dir: Path

    @classmethod
    def defaults(cls) -> SterilizerPaths:
        return cls(
            input_dir=DEFAULT_INPUT_DIR,
            output_dir=DEFAULT_OUTPUT_DIR,
            reports_dir=DEFAULT_REPORTS_DIR,
        )

    def input_file(self, name: str) -> Path:
        return self.input_dir / name

    def output_file(self, name: str) -> Path:
        return self.output_dir / name
