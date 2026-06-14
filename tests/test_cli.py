"""Tests for the CLI skeleton."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "data_sterilizer", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_shows_options() -> None:
    result = _run_cli("--help")

    assert result.returncode == 0
    assert "--input" in result.stdout
    assert "--output" in result.stdout
    assert "--report" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--strict" in result.stdout


def test_cli_rejects_non_pdf_report_path(tmp_path: Path) -> None:
    result = _run_cli("--report", str(tmp_path / "report.txt"))

    assert result.returncode != 0
    assert "pdf" in (result.stderr + result.stdout).lower()


def test_cli_dry_run_writes_pdf_only(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    report_path = tmp_path / "reports" / "run.pdf"
    input_dir.mkdir()

    source_root = PROJECT_ROOT / "Data_to_check"
    for file_name in ("patient.csv", "clinical.csv", "micro.csv"):
        (input_dir / file_name).write_text(
            (source_root / file_name).read_text(encoding="utf-8-sig"),
            encoding="utf-8",
        )

    result = _run_cli(
        "--input",
        str(input_dir),
        "--output",
        str(output_dir),
        "--report",
        str(report_path),
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert report_path.is_file()
    assert report_path.read_bytes()[:4] == b"%PDF"
    assert not output_dir.exists() or not any(output_dir.iterdir())
