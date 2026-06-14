# VetStats 2.0 — Data Sterilizer

Command-line tool for validating and cleaning veterinary patient datasets before they are used in VetStats 2.0 analysis.

## Purpose in VetStats 2.0

VetStats 2.0 works with three related CSV datasets: patient demographics, clinical visits, and microbiology results. Before any statistics or reporting can run, those files must be checked for structural problems, invalid values, and cross-table consistency.

The Data Sterilizer is the first step in that workflow. It:

1. Loads the raw CSV files from `Data_to_check/`
2. Validates them against the project rules
3. Applies automated cleaning corrections where rules allow
4. Re-validates the cleaned data, including cross-file referential integrity
5. Writes cleaned CSVs to `Sterile_data/`
6. Always produces a PDF validation report in `reports/`

The statistics GUI and other downstream VetStats modules are out of scope for this tool; it is CLI-only.

## What it does

For each run, the pipeline executes:

```
load → validate → clean → re-validate (with cross-file checks) → write CSVs → write PDF
```

**Input files** (semicolon-delimited, UTF-8):

| File | Description |
|------|-------------|
| `patient.csv` | Patient demographics and disease history |
| `clinical.csv` | Clinical visit and ulcer treatment records |
| `micro.csv` | Microbiology culture and susceptibility results |

**Output files** use the `_sterile.csv` suffix:

| File | Description |
|------|-------------|
| `patient_sterile.csv` | Cleaned patient data |
| `clinical_sterile.csv` | Cleaned clinical data |
| `micro_sterile.csv` | Cleaned micro data |

Existing files with the same `_sterile.csv` names in the output directory are overwritten on each run.

**Global cleaning** applied to all datasets includes lowercasing text, trimming whitespace, converting empty values to `xxx` (or `x` for micro susceptibility columns where applicable), dropping fully empty rows, dropping fully duplicated rows, and removing trailing `Unnamed:*` columns.

Dates are preserved in `dd.mm.yyyy` format throughout; the tool does not convert them to ISO format.

## Requirements

- Python 3.10 or newer
- `pandas>=2.0`
- `reportlab>=4.0`

## Installation

From the project root:

```bash
pip install -e .
```

For development dependencies (including pytest):

```bash
pip install -e ".[dev]"
```

Alternatively, install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

After installation, the CLI is available as:

```bash
python -m data_sterilizer
```

If the module is not found, run from the project root with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m data_sterilizer
```

## Input and output folders

| Folder | Role | Default path |
|--------|------|--------------|
| `Data_to_check/` | Raw input CSVs (`patient.csv`, `clinical.csv`, `micro.csv`) | Project root |
| `Sterile_data/` | Cleaned output CSVs (`patient_sterile.csv`, `clinical_sterile.csv`, `micro_sterile.csv`) | Project root |
| `reports/` | PDF validation reports | Project root |

These folders are gitignored. Place your source data in `Data_to_check/` before running the tool.

All three input files must exist in the input directory. The loader expects semicolon (`;`) delimiters.

## Usage

### Basic run (default paths)

```bash
python -m data_sterilizer
```

This reads from `Data_to_check/`, writes cleaned files to `Sterile_data/`, and generates a timestamped PDF in `reports/` (for example `reports/sterilizer_report_20260614_152300.pdf`).

### Custom paths and report file

```bash
python -m data_sterilizer \
  --input Data_to_check \
  --output Sterile_data \
  --report reports/my_run.pdf
```

### Dry run (validate and report only)

```bash
python -m data_sterilizer --dry-run --report reports/preview.pdf
```

No cleaned CSV files are written. The PDF report is still generated.

### Strict mode (fail on validation errors)

```bash
python -m data_sterilizer --strict
```

Exits with code `1` if any ERROR-level validation issues remain after cleaning. Without `--strict`, the tool still writes output and reports issues, but exits `0`.

## CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--input PATH` | `Data_to_check/` | Directory containing the three input CSV files |
| `--output PATH` | `Sterile_data/` | Directory for cleaned CSV output |
| `--report PATH` | Auto-generated timestamped PDF in `reports/` | PDF report output path (must end with `.pdf`) |
| `--dry-run` | off | Validate and report only; do not write cleaned CSVs |
| `--strict` | off | Exit with code `1` when ERROR-level issues remain |

On success, the CLI prints the PDF report path:

```
PDF report written to: reports/my_run.pdf
```

## PDF report contents

Every run produces a PDF report (never text or Markdown). The report includes:

1. **Title and metadata** — generation timestamp and run mode (`full run` or `dry-run`)
2. **Paths** — input, output, and reports directories used
3. **Dataset Summary** — row counts per dataset after load and after cleaning
4. **Validation Summary** — error count, warning count, and total issue count
5. **Cross-File Referential Integrity** — checks that every `patient_ID` in `clinical.csv` and `micro.csv` exists in `patient.csv`
6. **Table Issues** — per-dataset validation errors and warnings (patient, clinical, micro)
7. **Corrections** — automated cleaning actions applied (for example dropped trailing columns, filled missing dates)
8. **Output Files** — paths to written CSV files, or a note when no output was written (dry-run)

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Run completed; PDF written. With `--strict`, no ERROR-level issues remain. |
| `1` | Validation errors remain and `--strict` was used. |
| `2` | Runtime failure (for example missing input file, write error, or PDF generation error). |

## Running tests

```bash
pytest tests/ -q
```

## Project layout

```
Data_to_check/          # raw input (gitignored)
Sterile_data/           # cleaned output (gitignored)
reports/                # PDF reports (gitignored)
src/data_sterilizer/    # CLI, pipeline, validation, cleaning, reporting
tests/                  # pytest suite
```
