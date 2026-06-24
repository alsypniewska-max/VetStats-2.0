#!/usr/bin/env bash
# Double-clickable macOS launcher for VetStats 2.0 (opens in Terminal).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! "$ROOT/scripts/run_vetstats.sh" "$@"; then
  status=$?
  echo ""
  echo "VetStats 2.0 nie uruchomił się poprawnie (kod wyjścia: $status)."
  read -r -p "Naciśnij Enter, aby zamknąć to okno..."
  exit "$status"
fi
