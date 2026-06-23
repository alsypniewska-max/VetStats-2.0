#!/usr/bin/env bash
# Double-clickable macOS launcher for VetStats 2.0 (opens in Terminal).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/scripts/run_vetstats.sh" "$@"
