#!/usr/bin/env bash
# Launch the VetStats 2.0 GUI from a project checkout or editable install.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT/.matplotlib_cache}"
mkdir -p "$MPLCONFIGDIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "VetStats 2.0: python3 not found in PATH." >&2
  exit 127
fi

exec "$PYTHON" -m vetstats_app "$@"
