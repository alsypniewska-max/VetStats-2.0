#!/usr/bin/env bash
# Launch the VetStats 2.0 GUI using the project virtual environment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_PYTHON="$ROOT/.venv/bin/python"
SETUP_SCRIPT="$ROOT/scripts/setup_venv.sh"

_show_setup_help() {
  echo "Skonfiguruj środowisko jednorazowo:" >&2
  echo "  \"$SETUP_SCRIPT\"" >&2
  echo "" >&2
  echo "Ręcznie:" >&2
  echo "  cd \"$ROOT\"" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/pip install -e ." >&2
}

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "VetStats 2.0: nie znaleziono środowiska wirtualnego (.venv)." >&2
  echo "Aplikacja wymaga lokalnego .venv z zainstalowanymi zależnościami (m.in. SciPy)." >&2
  echo "" >&2
  _show_setup_help
  exit 1
fi

PYTHON="$VENV_PYTHON"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT/.matplotlib_cache}"
mkdir -p "$MPLCONFIGDIR"

MISSING=$("$PYTHON" - <<'PY' || true
import importlib
import sys

required = ("scipy", "pandas", "PyQt6", "matplotlib", "reportlab")
missing = []
for name in required:
    try:
        importlib.import_module(name)
    except ImportError:
        missing.append(name)
if missing:
    print(",".join(missing))
    sys.exit(1)
PY
)

if [[ -n "${MISSING:-}" ]]; then
  echo "VetStats 2.0: w .venv brakuje wymaganych bibliotek: ${MISSING//,/, }." >&2
  echo "Analiza statystyczna nie będzie działać bez pełnej instalacji zależności." >&2
  echo "" >&2
  _show_setup_help
  exit 1
fi

exec "$PYTHON" -m vetstats_app "$@"
